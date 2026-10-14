"""`casebench case`: a lawyer writes one case and approves it, or resolves its citations later."""

import getpass
from pathlib import Path

import click

from casebench.cases.build import Written, lawyer_case
from casebench.cases.draft import Draft, draft
from casebench.cases.resolve import resolve_case, unresolved
from casebench.cases.suite import existing, next_id, save
from casebench.config import DEFAULT_CONFIG, CasebenchConfig, load_config
from casebench.corpus.corpora import Corpora
from casebench.corpus.results import SearchResult
from casebench.extract.prompt import OUTCOMES
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.judge.resolve import Resolver

# Citations are typed on one line, separated by this; legal citations do not use it.
SEPARATOR = ";"
CONFIG = click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
SUITE = click.option(
    "--suite",
    "suite_dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
    help="The suite folder the case joins; it is created when it does not exist.",
)


def _config(path: Path) -> CasebenchConfig:
    return load_config(path) if path.is_file() else CasebenchConfig()


def _listed(values: list[str]) -> str:
    return f"{SEPARATOR} ".join(values)


def _split(typed: str) -> list[str]:
    return [value.strip() for value in typed.split(SEPARATOR) if value.strip()]


def _resolver(config: CasebenchConfig) -> Resolver | None:
    """The judge and the corpus find each citation's document, when the config has both."""
    if config.judge is None or not config.corpora:
        return None
    return Resolver(Judge(config.judge), Corpora(config.corpora), config.judge.candidates)


def _drafter(config: CasebenchConfig) -> Judge:
    """The first extraction model at its settings, else the judge (decision 0039)."""
    chosen = config.extract.models[0] if config.extract else config.judge
    if chosen is None:
        raise click.ClickException(
            "case new needs a model to draft with: add `extract:` models or a `judge:` to the "
            "config, or write the case with --manual"
        )
    return Judge(chosen)


def _shown(corpora: Corpora, result: SearchResult) -> str:
    """A decision by its citation as the corpus gives it, else its court, date and id."""
    if result.citation:
        return result.citation
    record = corpora.decision(result.id)
    return f"{record.court}, {record.date}, {result.id}"


def _pick(config: CasebenchConfig, topic: str, given: int | None) -> Draft:
    corpora = Corpora(config.corpora)
    shown = (
        config.judge.candidates if config.judge else JudgeConfig.model_fields["candidates"].default
    )
    found = corpora.search_results(topic, shown, kind="decision")
    if not found:
        raise click.ClickException(f"the corpus found no decision for {topic!r}; try other words")
    for number, result in enumerate(found, start=1):
        click.echo(f"  {number}. {_shown(corpora, result)}")
    chosen = given or click.prompt("which decision", type=click.IntRange(1, len(found)))
    if not 1 <= chosen <= len(found):
        raise click.BadParameter(f"pick one of 1 to {len(found)}", param_hint="--pick")
    model = _drafter(config)
    made = draft(model, corpora.decision(found[chosen - 1].id))
    spent = "cost unknown without a price" if made.cost is None else f"${made.cost:.3f}"
    click.echo(f"drafted by {made.model} in {made.seconds:.1f}s, {made.tokens} tokens, {spent}")
    return made


def _edit(made: Draft) -> Written:
    """Every drafted field, for the lawyer to keep or change."""
    reading = made.reading
    question = click.prompt("question", default=made.question or None)
    facts = click.prompt(
        "facts, without the ruling", default=reading.facts or "", show_default=False
    )
    outcome = click.prompt(
        f"outcome, one of {', '.join(OUTCOMES)} (empty for none)",
        default=reading.outcome.value if reading.outcome else "",
        type=click.Choice([*OUTCOMES, ""]),
        show_choices=False,
    )
    statutes = click.prompt(
        f"statutes the court relied on, separated by '{SEPARATOR}'",
        default=_listed([item.value for item in reading.statutes]),
    )
    precedents = click.prompt(
        f"precedents the court relied on, separated by '{SEPARATOR}'",
        default=_listed([item.value for item in reading.precedents]),
    )
    return Written(
        question=question,
        facts=facts,
        outcome=outcome or None,
        statutes=_split(statutes),
        precedents=_split(precedents),
    )


def _by_hand() -> Written:
    question = click.prompt("question")
    answer = click.prompt("the expected answer")
    statutes = click.prompt(
        f"statutes it rests on, separated by '{SEPARATOR}'", default="", show_default=False
    )
    precedents = click.prompt(
        f"precedents it rests on, separated by '{SEPARATOR}'", default="", show_default=False
    )
    return Written(
        question=question,
        answer=answer,
        statutes=_split(statutes),
        precedents=_split(precedents),
    )


@click.group(name="case")
def case_group() -> None:
    """Write one case and approve it."""


@case_group.command(name="new")
@SUITE
@click.option("--topic", help="What the case is about, in your words.")
@click.option("--pick", "given", type=int, help="Which listed decision, by its number.")
@click.option("--manual", is_flag=True, help="Write the question and answer by hand.")
@click.option("--author", help="Your name, as the case's reviewer.")
@CONFIG
def new_command(
    suite_dir: Path,
    topic: str | None,
    given: int | None,
    manual: bool,
    author: str | None,
    config_path: Path,
) -> None:
    """Find a decision on a topic, let one model draft the case from it, and approve it; or
    write it by hand."""
    config = _config(config_path)
    if not manual and not config.corpora:
        raise click.ClickException(
            "there is no corpus to search; add one with casebench corpus add, or write the case "
            "with --manual"
        )
    made = None
    if manual:
        written = _by_hand()
    else:
        made = _pick(config, topic or click.prompt("topic"), given)
        written = _edit(made)
    author = author or click.prompt("your name, as the case's reviewer", default=getpass.getuser())
    before, cases = existing(suite_dir)
    suite_id = before.suite_id if before else suite_dir.name
    case = lawyer_case(next_id(suite_id, cases), written, author, made)
    resolver = _resolver(config)
    if resolver is not None:
        case = resolve_case(case, resolver)
    if not click.confirm(f"add case {case.id} to {suite_dir}, approved by {author}?", default=True):
        raise click.Abort()
    old, manifest = save(suite_dir, [*cases, case])
    click.echo(f"added {case.id}: graded by {', '.join(case.metrics)}")
    waiting = unresolved(case)
    if waiting:
        later = "casebench case resolve" if resolver else "a corpus, then casebench case resolve"
        click.echo(f"  not in the corpus yet: {_listed(waiting)}; they resolve with {later}")
    click.echo(f"suite {manifest.suite_id}: {old or 'new'} -> {manifest.content_hash}")


@case_group.command(name="resolve")
@SUITE
@CONFIG
def resolve_command(suite_dir: Path, config_path: Path) -> None:
    """Resolve the citations lawyers wrote that no corpus document stood for yet."""
    resolver = _resolver(_config(config_path))
    if resolver is None:
        raise click.ClickException("resolving citations needs `judge:` and `corpus:` in the config")
    before, cases = existing(suite_dir)
    if before is None:
        raise click.ClickException(f"{suite_dir} holds no suite")
    waiting = [case for case in cases if unresolved(case)]
    updated = {case.id: resolve_case(case, resolver) for case in waiting}
    now = [updated.get(case.id, case) for case in cases]
    resolved = sum(len(unresolved(c)) for c in waiting) - sum(
        len(unresolved(c)) for c in updated.values()
    )
    old, manifest = save(suite_dir, now)
    click.echo(f"{resolved} citations resolved in {len(waiting)} cases")
    click.echo(f"suite {manifest.suite_id}: {old} -> {manifest.content_hash}")
