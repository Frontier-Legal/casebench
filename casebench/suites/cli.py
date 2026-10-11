"""`casebench generate`: freeze a court-derived suite from extracted answer keys."""

from datetime import date, datetime
from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, CasebenchConfig, load_config
from casebench.corpus.binding import Corpus
from casebench.extract.cli import DEFAULT_KEYS
from casebench.extract.run import read_keys
from casebench.judge.client import Judge
from casebench.judge.resolve import Resolver
from casebench.suites.court import FACT_KINDS, NotEnoughLevels, court_suite, unchanged
from casebench.suites.freeze import freeze
from casebench.suites.resolve import RESOLVED_KINDS, CaseResolver


def _resolver(config_path: Path) -> CaseResolver:
    """The court names authorities as written; the judge and the corpus find their documents."""
    config = load_config(config_path) if config_path.is_file() else CasebenchConfig()
    if config.judge is None or config.corpus is None:
        raise click.ClickException(
            "statute and precedent cases need `judge:` and `corpus:` in the config, "
            "to find the documents the court cited"
        )
    judge = Judge(config.judge)
    return CaseResolver(Resolver(judge, Corpus(config.corpus), config.judge.candidates))


@click.command(name="generate")
@click.option(
    "--keys",
    "keys_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_KEYS,
    show_default=True,
)
@click.option(
    "--types",
    default="outcome,statute,precedent",
    show_default=True,
    help="Comma-separated case types.",
)
@click.option("--n", "count", type=click.IntRange(min=1), required=True)
@click.option(
    "--after",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Only decisions dated after this day, such as a model's training cutoff.",
)
@click.option("--stratify", type=click.Choice(["court"]), help="Balance across court levels.")
@click.option("--suite-id", required=True, help="The suite's name; it also seeds its order.")
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), required=True)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
def generate_command(
    keys_dir: Path,
    types: str,
    count: int,
    after: datetime | None,
    stratify: str | None,
    suite_id: str,
    out: Path,
    config_path: Path,
) -> None:
    """Turn answer keys into cases and freeze them as a suite."""
    wanted = [t.strip() for t in types.split(",") if t.strip()]
    unknown = sorted(set(wanted) - set(FACT_KINDS))
    if unknown:
        raise click.BadParameter(f"unknown types {unknown}; choose from {sorted(FACT_KINDS)}")
    cutoff: date | None = after.date() if after else None
    resolver = _resolver(config_path) if set(wanted) & set(RESOLVED_KINDS) else None
    try:
        cases, generation = court_suite(
            suite_id,
            read_keys(keys_dir),
            wanted,
            count,
            after=cutoff,
            stratify=stratify == "court",
            resolve=resolver or unchanged,
        )
    except NotEnoughLevels as error:
        raise click.ClickException(str(error)) from error
    if resolver:
        generation["citations"] = resolver.report()
        for kind, counts in generation["citations"].items():
            click.echo(
                f"{kind}: {counts.get('resolved', 0)} court citations found in the corpus, "
                f"{counts.get('dropped', 0)} not found and dropped"
            )
    manifest = freeze(suite_id, cases, out, generation)
    if cutoff:
        click.echo(
            f"cutoff {cutoff}: {generation['decisions_allowed']} decisions allowed, "
            f"{generation['decisions_excluded_by_date']} excluded"
        )
    click.echo(f"suite {manifest.suite_id}: {manifest.case_count} cases {manifest.task_types}")
    click.echo(f"{manifest.content_hash}\n{out}")
