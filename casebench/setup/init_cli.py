"""`casebench init`: ask for the target, the corpus and the judge, and write casebench.yaml."""

from pathlib import Path
from typing import Any

import click
import httpx2
import yaml

from casebench.config import DEFAULT_CONFIG, ConfigError, load_config
from casebench.corpus.binding import CorpusConfig
from casebench.setup import catalog as model_catalog
from casebench.setup.advice import advice
from casebench.setup.catalog import families
from casebench.setup.checks import Status, live, offline
from casebench.setup.corpus_question import corpus_for_init
from casebench.setup.models import choose
from casebench.setup.routes import offers
from casebench.setup.scan import ModelName, Scan, Source, scan
from casebench.setup.sdks import detect
from casebench.setup.update import missing_from_models, model_additions, route_additions

HEADER = (
    "# Written by casebench init. It holds no secrets: API keys are read from the\n"
    "# environment variables named here, so this file can be committed and deployed.\n"
)


def _ask(given: str | None, label: str, default: str | None = None) -> str:
    return given if given is not None else click.prompt(label, default=default)


def _sdks(checkout: Path) -> list[str]:
    found = detect(checkout)
    if not found:
        return ["no SDK a parser reads; the proxy still records calls to the routes it knows"]
    return [f"{package}: read by the {parser} parser" for package, parser in found.items()]


def _source(source: Source | None) -> str:
    if source is None:
        return "its SDK's default"
    if source.env and source.literal:
        return f"from {source.env}, else {source.literal}"
    return f"from {source.env}" if source.env else source.literal or "unknown"


def _scanned(found: Scan) -> list[str]:
    """Every client with where its base URL and key come from, and every model named."""
    lines = []
    for client in found.clients:
        key = f", key {_source(client.api_key)}" if client.api_key else ""
        lines.append(f"{client.kind} at {client.where}, base URL {_source(client.base_url)}{key}")
    first: dict[str, ModelName] = {}
    for model in found.models:
        first.setdefault(model.name, model)
    lines += [f"model {m.name} at {m.path}:{m.line}" for m in first.values()]
    return [*lines, found.said()]


def _target(
    kind: str, entry: str | None, run: str | None, url: str | None, entries: list[str]
) -> dict[str, Any]:
    if kind == "python":
        if entry is None and entries:
            click.echo(
                f"the functions that call a model, nearest the question first: {', '.join(entries)}"
            )
        label = "the agent's function, as path.py:function"
        return {"type": "python", "entry": _ask(entry, label, entries[0] if entries else None)}
    if kind == "command":
        return {"type": "command", "run": _ask(run, "the command, with {question} where it goes")}
    return {
        "type": "http",
        "url": _ask(url, "the agent's endpoint"),
        "body": yaml.safe_load(click.prompt("the request body, as JSON with {question}")),
        "answer": click.prompt("JSONPath to the answer in the response"),
    }


def _routes(found: Scan, corpora: dict[str, Any], accept: bool | None) -> list[dict[str, Any]]:
    """A capture route for each client that can have one, offered one by one unless
    `--routes` or `--no-routes` answered for all (decision 0040)."""
    configs = {name: CorpusConfig.model_validate(block) for name, block in corpora.items()}
    chosen = []
    for offer in offers(found.clients, configs):
        where = f"{offer.client.kind} at {offer.client.where}"
        if offer.route is None:
            click.echo(f"capture  {where}: {offer.note}")
            continue
        wanted = (
            accept
            if accept is not None
            else click.confirm(f"record {where} through the proxy: {offer.note}?", default=True)
        )
        if wanted:
            chosen.append(offer.route)
            click.echo(f"capture  {where}: {offer.note}")
    return chosen


def _same_family(judge: dict[str, Any], found: Scan, catalog: dict[str, Any]) -> str | None:
    """As `casebench run` warns: a judge of the family the agent's models come from favours
    their answers (decision 0029)."""
    family = (judge.get("options") or {}).get("family")
    if family is None:
        family = families(catalog, [judge["model"]]).get(judge["model"])
    named = families(catalog, [m.name for m in found.models])
    same = sorted(name for name, of in named.items() if of == family)
    if not family or not same:
        return None
    return (
        f"warning: the judge is of the {family} family, like {', '.join(same)} in your agent's "
        "code; a model grading its own family's answers favours them (decision 0029). Pick a "
        "judge from another family."
    )


def _update(config_path: Path, found: Scan, catalog_path: Path | None, routes: bool | None) -> None:
    """Only what this version adds and the config lacks, offered and then written; every
    setting already there stays as written (decision 0042)."""
    config = load_config(config_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    additions = [] if routes is False else route_additions(data, config, found)
    if missing_from_models(data):
        try:
            additions += model_additions(data, model_catalog.load(catalog_path))
        except httpx2.HTTPError as error:
            click.echo(f"the model catalog could not be fetched ({error}); pass --catalog FILE")
    for line in advice(config):
        if line.startswith("corpus"):
            click.echo(f"could use {line}")
    if not additions:
        click.echo(f"{config_path} has everything this version adds; nothing to change")
        return
    for addition in additions:
        click.echo(f"add      {addition.said}")
    asked = f"add these to {config_path}? its settings stay; comments other than its header do not"
    if routes is None and not click.confirm(asked, default=True):
        raise click.Abort()
    for addition in additions:
        addition.apply(data)
    config_path.write_text(
        HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    load_config(config_path)
    click.echo(f"updated  {config_path}; run `casebench check` where it runs")


def _options(pairs: tuple[str, ...]) -> dict[str, Any]:
    """NAME=VALUE pairs; each value read as YAML, so numbers stay numbers."""
    options = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep:
            raise click.BadParameter(f"{pair!r} must look like NAME=VALUE")
        options[name] = yaml.safe_load(value)
    return options


@click.command(name="init")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option("--target", "target_kind", type=click.Choice(["python", "command", "http"]))
@click.option("--entry", help="A Python target's function, as path.py:function.")
@click.option("--run", "run_line", help="A command target's command line.")
@click.option("--url", help="An HTTP target's endpoint.")
@click.option("--corpus", "corpus_kind", type=click.Choice(["folder", "http", "mcp", "none"]))
@click.option("--corpus-path", help="A folder corpus's path.")
@click.option(
    "--profile",
    "profiles",
    multiple=True,
    metavar="FILE_OR_ID",
    help="A data provider's profile, a file or a bundled id; give it once for each provider.",
)
@click.option("--judge-provider", help="The judge's provider, as the model catalog names it.")
@click.option("--judge-model")
@click.option(
    "--judge-option", "judge_options", multiple=True, help="NAME=VALUE, over the catalog's."
)
@click.option("--no-judge", is_flag=True, help="Set no judge; outcome suites need none.")
@click.option(
    "--extract",
    "extract_models",
    nargs=2,
    multiple=True,
    metavar="PROVIDER MODEL",
    help="An extraction model; give it twice, for two different models.",
)
@click.option("--no-extract", is_flag=True, help="Set no extraction models.")
@click.option(
    "--catalog",
    "catalog_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="A saved copy of the model catalog, instead of fetching it.",
)
@click.option("--no-live", is_flag=True, help="Only the checks that need no network.")
@click.option(
    "--routes/--no-routes",
    "routes",
    default=None,
    help="Write a capture route for every client found, or for none, without asking.",
)
def init_command(
    config_path: Path,
    target_kind: str | None,
    entry: str | None,
    run_line: str | None,
    url: str | None,
    corpus_kind: str | None,
    corpus_path: str | None,
    profiles: tuple[str, ...],
    judge_provider: str | None,
    judge_model: str | None,
    judge_options: tuple[str, ...],
    no_judge: bool,
    extract_models: tuple[tuple[str, str], ...],
    no_extract: bool,
    catalog_path: Path | None,
    no_live: bool,
    routes: bool | None,
) -> None:
    """Set Casebench up for the agent in this folder, or bring an existing setup up to date."""
    checkout = config_path.resolve().parent
    for line in _sdks(checkout):
        click.echo(f"found    {line}")
    found = scan(checkout)
    for line in _scanned(found):
        click.echo(f"found    {line}")
    if config_path.exists():
        _update(config_path, found, catalog_path, routes)
        return
    kind = target_kind or click.prompt(
        "how Casebench reaches the agent", type=click.Choice(["python", "command", "http"])
    )
    data: dict[str, Any] = {"target": _target(kind, entry, run_line, url, found.entries)}
    corpora, live_checked = corpus_for_init(corpus_kind, corpus_path, profiles)
    if corpora:
        data["corpora"] = corpora
    chosen_routes = _routes(found, corpora, routes)
    if chosen_routes:
        data["capture"] = {"routes": chosen_routes}
    catalog: dict[str, Any] | None = None

    def listed() -> dict[str, Any]:
        nonlocal catalog
        if catalog is None:
            try:
                catalog = model_catalog.load(catalog_path)
            except httpx2.HTTPError as error:
                raise click.ClickException(
                    f"the model catalog could not be fetched ({error}); pass --catalog FILE"
                ) from error
        return catalog

    if not no_judge:
        data["judge"], notes = choose(
            "judge", listed(), judge_provider, judge_model, _options(judge_options)
        )
        click.echo(f"judge    {'; '.join(notes)}")
        warning = _same_family(data["judge"], found, listed())
        if warning:
            click.echo(warning, err=True)
    wants_extract = bool(extract_models) or (
        not no_extract
        and click.confirm(
            "make test cases from your court decisions? two different models read each "
            "decision to find the ruling, statutes and precedents",
            default=True,
        )
    )
    if wants_extract:
        given = list(extract_models) or [(None, None), (None, None)]
        if len(given) != 2:
            raise click.UsageError("--extract takes two models: give it twice")
        chosen = []
        for number, (provider, model) in enumerate(given, start=1):
            block, notes = choose(f"extraction model {number}", listed(), provider, model, {})
            click.echo(f"extract  {'; '.join(notes)}")
            chosen.append(block)
        data["extract"] = {"models": chosen}
    config_path.write_text(
        HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    try:
        problems = offline(load_config(config_path))
    except ConfigError as error:
        config_path.unlink()
        raise click.ClickException(str(error)) from error
    if problems:
        config_path.unlink()
        raise click.ClickException("; ".join(p.line() for p in problems))
    click.echo(f"wrote    {config_path}")
    if no_live:
        click.echo("run `casebench check` where the corpus, the target and the judge are reachable")
        return
    checked = load_config(config_path)
    # A corpus whose live search and fetch just ran is not checked again.
    rest = {name: c for name, c in checked.corpora.items() if name not in live_checked}
    checked = checked.model_copy(update={"corpora": rest})
    checks = live(checked)
    for item in checks:
        click.echo(item.line())
    if any(item.status is not Status.PASSED for item in checks):
        click.echo("run `casebench check` where the rest is reachable, before `casebench run`")
