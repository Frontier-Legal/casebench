"""`casebench corpus add http|mcp`: describe a store from one live search and fetch."""

import os
import re
from pathlib import Path
from typing import Any

import click
import httpx2

from casebench.config import DEFAULT_CONFIG
from casebench.corpus.add import ConfigHasCorpus, corpus_block, describe, write_corpus
from casebench.corpus.mapping import every, record_fields
from casebench.corpus.record import REQUIRED_FIELDS
from casebench.corpus.suggest import document_fields, search_ids
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.targets.placeholders import split_command

FIELDS = (*REQUIRED_FIELDS, "level")
VARIABLE = re.compile(r"\$\{(\w+)\}")


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


def _live(call: Any, what: str) -> Any:
    """A refused request says why in the user's terms; a connection that fails propagates."""
    try:
        return call()
    except httpx2.HTTPStatusError as error:
        status = error.response.status_code
        hint = (
            "it needs an API key, or the key it got is wrong"
            if status in (401, 403)
            else "check the paths and the search"
        )
        raise click.ClickException(f"the API answered {status} to the {what}: {hint}") from error


def _map(
    store: Any, probe: str, ids_given: str | None, fields_given: dict[str, str], ask: bool
) -> tuple[str, dict[str, str]]:
    """One live search and one fetch; show them, suggest paths, let the user correct them."""
    results = _live(lambda: store.search_raw(probe, 1), "search")
    click.echo(f"search for {probe!r} returned:")
    for line in describe(results):
        click.echo(f"  {line}")
    ids_path = _choose(
        "JSONPath to the ids in a search result", ids_given, search_ids(results), ask
    )
    if not ids_path or not every(ids_path, results):
        raise click.ClickException("no document id found in the search result; check the path")
    first_id = str(every(ids_path, results)[0])
    document = _live(lambda: store.fetch_raw(first_id), f"fetch of document {first_id}")
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


def _ask(given: str | None, question: str, ask: bool, default: str | None = None) -> str:
    if given:
        return given
    if not ask:
        if default is not None:
            return default
        raise click.UsageError(f"missing: {question}")
    return click.prompt(question, default=default)


def key_header(key_env: str | None, header: str) -> dict[str, str]:
    """`Authorization` takes the key as a bearer token (RFC 6750); another header takes it
    as it is. The value names the variable; the key itself is never written down."""
    if not key_env:
        return {}
    return {header: f"Bearer ${{{key_env}}}" if header == "Authorization" else f"${{{key_env}}}"}


def http_block(
    *,
    base_url: str | None = None,
    search_path: str | None = None,
    query_param: str = "q",
    fetch_path: str | None = None,
    headers: tuple[str, ...] = (),
    key_env: str | None = None,
    key_header_name: str = "Authorization",
    probe: str | None = None,
    ids_path: str | None = None,
    fields: tuple[str, ...] = (),
    jurisdiction: str | None = None,
    ask: bool = True,
) -> dict[str, Any]:
    """Ask for what was not given, make one live search and fetch, and return the corpus block."""
    base_url = _ask(
        base_url, "the document API's root URL, such as https://api.example.com/v1", ask
    )
    search_path = _ask(search_path, "the path that searches, under that URL, such as /search", ask)
    fetch_path = _ask(
        fetch_path,
        "the path that returns one document, with {id} where its id goes, such as /documents/{id}",
        ask,
    )
    if "{id}" not in fetch_path:
        raise click.BadParameter(f"{fetch_path!r} has no {{id}} for the document's id")
    sent = _pairs(headers)
    if not sent and key_env is None and ask:
        key_env = click.prompt(
            "the environment variable that holds its API key (leave empty if it needs none)",
            default="",
            show_default=False,
        )
    sent |= key_header(key_env or None, key_header_name)
    options: dict[str, Any] = {
        "base_url": base_url,
        "headers": sent,
        "search_path": search_path,
        "search_params": {query_param: "{text}"},
        "fetch_path": fetch_path,
    }
    unset = sorted(set(VARIABLE.findall(" ".join(sent.values()))) - set(os.environ))
    if unset:
        raise click.ClickException(f"{', '.join(unset)} is not set in this shell; export it first")
    probe = _ask(probe, "a search that finds at least one document", ask)
    store = connector("http", options)
    options["search_ids"], options["fields"] = _map(store, probe, ids_path, _pairs(fields), ask)
    return corpus_block("http", options, jurisdiction)


def mcp_block(
    *,
    command_line: str | None = None,
    url: str | None = None,
    search_tool: str | None = None,
    search_arg: str = "query",
    fetch_tool: str | None = None,
    fetch_arg: str = "id",
    probe: str | None = None,
    ids_path: str | None = None,
    fields: tuple[str, ...] = (),
    jurisdiction: str | None = None,
    ask: bool = True,
) -> dict[str, Any]:
    if not command_line and not url:
        if not ask:
            raise click.UsageError("pass --command or --url")
        reached = click.prompt(
            "how to reach the MCP server: a command that starts it, or its URL"
        ).strip()
        url, command_line = (reached, None) if reached.startswith("http") else (None, reached)
    options: dict[str, Any] = (
        {"command": split_command(command_line)} if command_line else {"url": url}
    )
    lister = connector("mcp", options)
    for name, description, _ in lister.tools():
        click.echo(f"  {name}: {description}")
    lister.close()
    options["search_tool"] = _ask(search_tool, "the tool that searches", ask)
    options["search_arguments"] = {search_arg: "{text}"}
    options["fetch_tool"] = _ask(fetch_tool, "the tool that returns one document", ask)
    options["fetch_arguments"] = {fetch_arg: "{id}"}
    probe = _ask(probe, "a search that finds at least one document", ask)
    store = connector("mcp", options)
    try:
        options["search_ids"], options["fields"] = _map(store, probe, ids_path, _pairs(fields), ask)
    finally:
        store.close()
    return corpus_block("mcp", options, jurisdiction)


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
@click.option("--base-url", help="The API's root URL, such as https://api.example.com/v1.")
@click.option("--search-path", help="Such as /search.")
@click.option("--query-param", default="q", show_default=True)
@click.option("--fetch-path", help="With {id}, such as /documents/{id}.")
@click.option("--key-env", help="The environment variable that holds the API key.")
@click.option(
    "--key-header",
    default="Authorization",
    show_default=True,
    help="The header that carries the key; Authorization sends it as a bearer token.",
)
@click.option(
    "--header",
    "headers",
    multiple=True,
    help="NAME=VALUE; ${VAR} reads the environment, such as Authorization=Bearer ${KEY}.",
)
@common
def http(
    base_url: str | None,
    search_path: str | None,
    query_param: str,
    fetch_path: str | None,
    key_env: str | None,
    key_header: str,
    headers: tuple[str, ...],
    config_path: Path,
    probe: str | None,
    ids_path: str | None,
    fields: tuple[str, ...],
    jurisdiction: str | None,
    yes: bool,
) -> None:
    """A document API reached over HTTP."""
    block = http_block(
        base_url=base_url,
        search_path=search_path,
        query_param=query_param,
        fetch_path=fetch_path,
        headers=headers,
        key_env=key_env,
        key_header_name=key_header,
        probe=probe,
        ids_path=ids_path,
        fields=fields,
        jurisdiction=jurisdiction,
        ask=not yes,
    )
    _save(config_path, block, not yes)


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
    block = mcp_block(
        command_line=command_line,
        url=url,
        search_tool=search_tool,
        search_arg=search_arg,
        fetch_tool=fetch_tool,
        fetch_arg=fetch_arg,
        probe=probe,
        ids_path=ids_path,
        fields=fields,
        jurisdiction=jurisdiction,
        ask=not yes,
    )
    _save(config_path, block, not yes)
