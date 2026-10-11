"""`casebench corpus add http|mcp`: describe a store from one live search and fetch."""

from pathlib import Path
from typing import Any

import click

from casebench.config import DEFAULT_CONFIG
from casebench.corpus.add import ConfigHasCorpus, corpus_block, describe, write_corpus
from casebench.corpus.mapping import every, record_fields
from casebench.corpus.record import REQUIRED_FIELDS
from casebench.corpus.suggest import document_fields, search_ids
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.targets.placeholders import split_command

FIELDS = (*REQUIRED_FIELDS, "level")


def connector(name: str, options: dict[str, Any]) -> Any:
    """A built-in connector, loaded through the registry like any other plugin."""
    return registry.load(kind_named("connector"), name)(**options)


def _pairs(values: tuple[str, ...]) -> dict[str, str]:
    pairs = {}
    for value in values:
        name, sep, rest = value.partition("=")
        if not sep:
            raise click.BadParameter(f"{value!r} must look like NAME=VALUE")
        pairs[name] = rest
    return pairs


def _choose(label: str, given: str | None, suggestion: str | None, ask: bool) -> str | None:
    if given is not None or not ask:
        return given if given is not None else suggestion
    return click.prompt(label, default=suggestion or "", show_default=bool(suggestion)) or None


def _map(
    store: Any, probe: str, ids_given: str | None, fields_given: dict[str, str], ask: bool
) -> tuple[str, dict[str, str]]:
    """One live search and one fetch; show them, suggest paths, let the user correct them."""
    results = store.search_raw(probe, 1)
    click.echo(f"search for {probe!r} returned:")
    for line in describe(results):
        click.echo(f"  {line}")
    ids_path = _choose(
        "JSONPath to the ids in a search result", ids_given, search_ids(results), ask
    )
    if not ids_path or not every(ids_path, results):
        raise click.ClickException("no document id found in the search result; check the path")
    first_id = str(every(ids_path, results)[0])
    document = store.fetch_raw(first_id)
    click.echo(f"document {first_id} returned:")
    for line in describe(document):
        click.echo(f"  {line}")
    suggested = document_fields(document)
    fields = {}
    for name in FIELDS:
        path = _choose(f"JSONPath to {name}", fields_given.get(name), suggested.get(name), ask)
        if path:
            fields[name] = path
    mapped = record_fields(document, fields)
    missing = [name for name in REQUIRED_FIELDS if name not in mapped]
    click.echo("missing: " + ", ".join(missing) if missing else "every required field found")
    return ids_path, fields


def _save(config: Path, block: dict[str, Any], ask: bool) -> None:
    if ask and not click.confirm(f"write this corpus into {config}?", default=True):
        raise click.Abort()
    try:
        click.echo(write_corpus(config, block))
    except ConfigHasCorpus as error:
        raise click.ClickException(str(error)) from error


COMMON = [
    click.option(
        "--config",
        "config_path",
        type=click.Path(dir_okay=False, path_type=Path),
        default=DEFAULT_CONFIG,
        show_default=True,
    ),
    click.option("--probe", help="A search that finds at least one document."),
    click.option("--ids", "ids_path", help="JSONPath to the ids in a search result."),
    click.option("--field", "fields", multiple=True, help="NAME=JSONPath, such as text=$.body."),
    click.option("--jurisdiction", help="Read only this jurisdiction's documents."),
    click.option("--yes", is_flag=True, help="Ask nothing: take the flags and suggestions."),
]


def common(command: Any) -> Any:
    for option in reversed(COMMON):
        command = option(command)
    return command


@click.group()
def add() -> None:
    """Add the document store citations are checked against."""


@add.command()
@click.option("--base-url", prompt=True)
@click.option("--search-path", prompt=True, help="Such as /search.")
@click.option("--query-param", default="q", show_default=True)
@click.option("--fetch-path", prompt=True, help="With {id}, such as /documents/{id}.")
@click.option(
    "--header",
    "headers",
    multiple=True,
    help="NAME=VALUE; ${VAR} reads the environment, such as Authorization=Bearer ${KEY}.",
)
@common
def http(
    base_url: str,
    search_path: str,
    query_param: str,
    fetch_path: str,
    headers: tuple[str, ...],
    config_path: Path,
    probe: str | None,
    ids_path: str | None,
    fields: tuple[str, ...],
    jurisdiction: str | None,
    yes: bool,
) -> None:
    """A document API reached over HTTP."""
    options: dict[str, Any] = {
        "base_url": base_url,
        "headers": _pairs(headers),
        "search_path": search_path,
        "search_params": {query_param: "{text}"},
        "fetch_path": fetch_path,
    }
    probe = probe or click.prompt("a search that finds a document")
    store = connector("http", options)
    options["search_ids"], options["fields"] = _map(store, probe, ids_path, _pairs(fields), not yes)
    _save(config_path, corpus_block("http", options, jurisdiction), not yes)


@add.command()
@click.option("--command", "command_line", help="Start the server over stdio.")
@click.option("--url", help="Reach the server over Streamable HTTP.")
@click.option("--search-tool")
@click.option("--search-arg", default="query", show_default=True)
@click.option("--fetch-tool")
@click.option("--fetch-arg", default="id", show_default=True)
@common
def mcp(
    command_line: str | None,
    url: str | None,
    search_tool: str | None,
    search_arg: str,
    fetch_tool: str | None,
    fetch_arg: str,
    config_path: Path,
    probe: str | None,
    ids_path: str | None,
    fields: tuple[str, ...],
    jurisdiction: str | None,
    yes: bool,
) -> None:
    """An MCP server with a search tool and a fetch tool."""
    if not command_line and not url:
        raise click.UsageError("pass --command or --url")
    options: dict[str, Any] = (
        {"command": split_command(command_line)} if command_line else {"url": url}
    )
    lister = connector("mcp", options)
    for name, description, _ in lister.tools():
        click.echo(f"  {name}: {description}")
    lister.close()
    options["search_tool"] = search_tool or click.prompt("search tool")
    options["search_arguments"] = {search_arg: "{text}"}
    options["fetch_tool"] = fetch_tool or click.prompt("fetch tool")
    options["fetch_arguments"] = {fetch_arg: "{id}"}
    probe = probe or click.prompt("a search that finds a document")
    store = connector("mcp", options)
    try:
        options["search_ids"], options["fields"] = _map(
            store, probe, ids_path, _pairs(fields), not yes
        )
    finally:
        store.close()
    _save(config_path, corpus_block("mcp", options, jurisdiction), not yes)
