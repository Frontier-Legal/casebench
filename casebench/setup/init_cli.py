"""`casebench init`: walk a team through setting Casebench up for its agent, and write it down."""

import os
from pathlib import Path
from typing import Any

import click
import httpx2
import yaml

from casebench.config import DEFAULT_CONFIG, ConfigError, load_config
from casebench.corpus.binding import CorpusConfig
from casebench.key_record import record_keys
from casebench.perimeter import enforce
from casebench.setup import catalog as model_catalog
from casebench.setup import screen
from casebench.setup.advice import advice
from casebench.setup.catalog import families
from casebench.setup.checks import Status, live, offline
from casebench.setup.corpus_question import corpus_for_init
from casebench.setup.judge_question import ask_model
from casebench.setup.key_question import KeyFound, given_files, given_keys, preset
from casebench.setup.picker import confirm, interactive, pick, text
from casebench.setup.routes import offers
from casebench.setup.scan import Scan, scan
from casebench.setup.summary import details as scan_details
from casebench.setup.summary import summary
from casebench.setup.update import missing_from_models, model_additions, route_additions

HEADER = (
    "# Written by casebench init. It holds no secrets: API keys are read from the\n"
    "# environment variables named here, or from the .env files `keys:` names for them,\n"
    "# so this file can be committed and deployed.\n"
)
LANES = [
    ("Quick start (recommended): use what was found, ask only what's missing", "quick"),
    ("Custom: choose every part", "custom"),
]
KINDS = [
    ("a Python function in this project", "python"),
    ("an HTTP endpoint", "http"),
    ("a command", "command"),
]
OTHER = "\0other"


def _lane(given: bool | None) -> bool:
    """True for Custom. Without a terminal and without a flag, every part is asked, as a
    script answering init's questions expects."""
    if given is not None:
        return given
    if not interactive():
        return True
    return pick("How do you want to start?", LANES, "quick") == "custom"


def _entry(given: str | None, entries: list[str], custom: bool) -> str:
    """Picked from the functions Casebench can call with a case's inputs; typed only when it
    is none of them. None is suggested over another; in Quick start the only one there is is
    taken, since there is nothing to choose (decision 0043)."""
    if given is not None:
        return given
    if len(entries) == 1 and not custom:
        screen.ok(f"agent {entries[0]}, the one function Casebench can call")
        return entries[0]
    if not entries:
        return text("the agent's function, as path.py:function")
    choices = [(entry, entry) for entry in entries]
    chosen = pick("Which function answers a question?", [*choices, ("another function…", OTHER)])
    return text("the agent's function, as path.py:function") if chosen == OTHER else chosen


def _target(
    kind: str | None,
    entry: str | None,
    run: str | None,
    url: str | None,
    found: Scan,
    custom: bool,
) -> dict[str, Any]:
    given = [name for name, value in (("python", entry), ("command", run), ("http", url)) if value]
    if kind is None and len(given) == 1:
        kind = given[0]  # a function, command or endpoint given says how it is reached
    if kind is None:
        quick_python = not custom and bool(found.entries)
        kind = "python" if quick_python else pick("How does Casebench reach your agent?", KINDS)
    if kind == "python":
        return {"type": "python", "entry": _entry(entry, found.entries, custom)}
    if kind == "command":
        return {"type": "command", "run": run or text("the command, with {question} where it goes")}
    return {
        "type": "http",
        "url": url or text("the agent's endpoint"),
        "body": yaml.safe_load(text("the request body, as JSON with {question}")),
        "answer": text("JSONPath to the answer in the response"),
    }


def _routes(found: Scan, corpora: dict[str, Any], accept: bool | None) -> list[dict[str, Any]]:
    """A capture route for each client that can have one, offered one by one unless
    `--routes`, `--no-routes` or Quick start answered for all (decision 0040)."""
    configs = {name: CorpusConfig.model_validate(block) for name, block in corpora.items()}
    chosen = []
    for offer in offers(found.clients, configs):
        where = f"{offer.client.kind} at {offer.client.where}"
        if offer.route is None:
            screen.line(f"{where}: {offer.note}", "dim")
            continue
        wanted = accept if accept is not None else confirm(f"Record {where}? {offer.note}")
        if wanted:
            chosen.append(offer.route)
            screen.ok(f"{where}: {offer.note}")
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
            screen.warn(f"the model catalog could not be fetched ({error}); pass --catalog FILE")
    for line in advice(config):
        if line.startswith("corpus"):
            screen.line(f"could use {line}", "yellow")
    if not additions:
        screen.outro([f"{config_path} has everything this version adds; nothing to change"])
        return
    screen.step("What this version adds")
    for addition in additions:
        screen.line(f"add {addition.said}")
    asked = f"Add these to {config_path}? Its settings stay; comments other than its header do not"
    if routes is None and not confirm(asked):
        raise click.Abort()
    for addition in additions:
        addition.apply(data)
    config_path.write_text(
        HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    load_config(config_path)
    screen.outro([f"Updated {config_path}.", "Next: casebench check, where it runs"])


def _options(pairs: tuple[str, ...]) -> dict[str, Any]:
    """NAME=VALUE pairs; each value read as YAML, so numbers stay numbers."""
    options = {}
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep:
            raise click.BadParameter(f"{pair!r} must look like NAME=VALUE")
        options[name] = yaml.safe_load(value)
    return options


def _keys(found: list[KeyFound], folder: Path) -> dict[str, str]:
    """Each key read from a file, by name and the file relative to the config: never a value."""
    return {
        key.name: os.path.relpath(key.file, folder).replace(os.sep, "/")
        for key in found
        if key.file is not None
    }


def _model_line(block: dict[str, Any], keys: dict[str, str]) -> str:
    key = (block.get("options") or {}).get("api_key_env")
    where = f" · key {key}" + (f", read from {keys[key]}" if key in keys else "") if key else ""
    return f"{block['provider']} {block['model']}{where}"


def _review(data: dict[str, Any]) -> list[tuple[str, str]]:
    """What casebench.yaml will hold, a line per part, as the review shows it."""
    keys = data.get("keys", {})
    target = data["target"]
    rows = [("target", str(target.get("entry") or target.get("run") or target.get("url")))]
    for name, corpus in (data.get("corpora") or {}).items():
        options = corpus.get("options", {})
        where = options.get("base_url") or options.get("path") or options.get("url") or ""
        rows.append((f"corpus {name}", f"{corpus['connector']} {where}".strip()))
    if "judge" in data:
        rows.append(("judge", _model_line(data["judge"], keys)))
    for number, model in enumerate((data.get("extract") or {}).get("models", []), start=1):
        rows.append((f"extraction {number}", _model_line(model, keys)))
    routes = [r["name"] for r in (data.get("capture") or {}).get("routes", [])]
    if routes:
        rows.append(("capture", ", ".join(routes)))
    for name, file in keys.items():
        rows.append(("key", f"{name}, read from {file}"))
    return rows


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
@click.option(
    "--custom/--quick",
    "custom",
    default=None,
    help="Choose every part, or take what was found and ask only what is missing.",
)
@click.option(
    "--key",
    "key_files",
    multiple=True,
    metavar="NAME=FILE",
    help="The .env file a key is read from, relative to the config; give it once for each.",
)
@click.option("--yes", is_flag=True, help="Write casebench.yaml without asking after the review.")
@click.option("--details", is_flag=True, help="List everything the code scan found.")
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
    custom: bool | None,
    key_files: tuple[str, ...],
    yes: bool,
    details: bool,
) -> None:
    """Set Casebench up for the agent in this folder, or bring an existing setup up to date."""
    checkout = config_path.resolve().parent
    preset(given_keys(key_files, checkout))
    updating = config_path.exists()
    screen.intro(f"{'updating' if updating else 'setting up'} {checkout.name}")
    screen.step("Reading your project")
    with screen.working("reading your project"):
        found = scan(checkout)
    screen.rows(summary(found, checkout, entry))
    if details:
        for line in scan_details(found):
            screen.line(line, "dim")
    if updating:
        for name, file in record_keys(config_path, given_files(checkout)).items():
            screen.ok(f"key {name}: read from {file}, by name")
        _update(config_path, found, catalog_path, routes)
        return
    choose_all = _lane(custom)
    screen.step("Your agent")
    data: dict[str, Any] = {"target": _target(target_kind, entry, run_line, url, found, choose_all)}
    screen.step("Court decisions")
    sources = corpus_for_init(corpus_kind, corpus_path, profiles, checkout, choose_all)
    if sources.corpora:
        data["corpora"] = sources.corpora
    if found.clients and data["target"].get("type") == "python":
        # Its worker sends each call through the proxy to where it goes (decision 0044).
        screen.step("Recording your agent's calls")
        screen.line("each model and search call is recorded where it goes; no route is needed")
    elif found.clients:
        screen.step("Recording your agent's calls")
        accept = routes if routes is not None or choose_all else True
        chosen_routes = _routes(found, sources.corpora, accept)
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

    keys = list(sources.keys)
    unchecked: list[str] = ["corpus"] if sources.missed else []
    if not no_judge:
        screen.step("The judge")
        data["judge"], key, answered = ask_model(
            "judge",
            listed,
            checkout,
            judge_provider,
            judge_model,
            _options(judge_options),
            live=not no_live,
        )
        keys += [key] if key else []
        unchecked += [] if answered or no_live else ["judge"]
        warning = _same_family(data["judge"], found, listed())
        if warning:
            screen.warn(warning)
            click.echo(warning, err=True)
    asks_extract = choose_all and not no_extract
    wants_extract = bool(extract_models) or (
        asks_extract
        and confirm(
            "Make test cases from many court decisions too? Two different models read each "
            "decision to find the ruling, statutes and precedents"
        )
    )
    if wants_extract:
        screen.step("Extraction models")
        given = list(extract_models) or [(None, None), (None, None)]
        if len(given) != 2:
            raise click.UsageError("--extract takes two models: give it twice")
        chosen = []
        for number, (provider, model) in enumerate(given, start=1):
            block, key, answered = ask_model(
                f"extraction model {number}", listed, checkout, provider, model, live=not no_live
            )
            keys += [key] if key else []
            unchecked += [] if answered or no_live else [f"extraction model {number}"]
            chosen.append(block)
        data["extract"] = {"models": chosen}
    elif not choose_all and not no_extract:
        screen.line("test cases from many decisions can come later: casebench extract", "dim")
    if found_keys := {**_keys(keys, checkout), **given_files(checkout)}:
        data["keys"] = found_keys
    screen.review(f"{config_path.name} will hold", _review(data))
    if not yes and not confirm(f"Write {config_path}?"):
        screen.outro(["Nothing was written."])
        raise SystemExit(0)
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
    screen.ok(f"wrote {config_path}")
    if no_live:
        screen.outro(
            [
                f"Wrote {config_path}.",
                "Next: casebench check, where the corpus, the agent and the judge are reachable",
            ]
        )
        return
    checked = load_config(config_path)
    enforce(checked)
    # What init already checked live (corpora, judge, extraction models) is not asked again.
    rest = {name: c for name, c in checked.corpora.items() if name not in sources.checked}
    checked = checked.model_copy(update={"corpora": rest, "judges": [], "extract": None})
    with screen.working("checking your agent answers"):
        checks = live(checked)
    for item in checks:
        if item.status is Status.PASSED:
            screen.ok(f"{item.name}: {item.detail}")
        else:
            screen.fail(f"{item.name} {item.status.value}: {item.detail}")
    failed = unchecked or any(item.status is not Status.PASSED for item in checks)
    screen.outro(
        [
            "Ready." if not failed else "Written; some parts are not reachable from here.",
            "Next: casebench case new --suite first     write one case",
            "      casebench run --suite first          ask your agent and grade it",
            *(
                ["      casebench check                      where the rest is reachable"]
                if failed
                else []
            ),
        ]
    )
