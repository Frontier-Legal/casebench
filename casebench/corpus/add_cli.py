"""`casebench corpus add http|mcp|profile`: describe a store from one live search and fetch."""

import json
import re
import shutil
from pathlib import Path
from typing import Any

import click
import httpx2

from casebench import keys
from casebench.config import DEFAULT_CONFIG, load_config
from casebench.core.jurisdiction import UnknownJurisdiction, code
from casebench.corpus.add import (
    ConfigHasCorpus,
    corpus_block,
    describe,
    name_for,
    taken_names,
    write_corpus,
)
from casebench.corpus.bundled import resolve
from casebench.corpus.from_profile import ProfileProblem, profile_block
from casebench.corpus.ids import NAME
from casebench.corpus.mapping import every, record_fields
from casebench.corpus.record import REQUIRED_FIELDS
from casebench.corpus.results import read_results
from casebench.corpus.suggest import (
    document_fields,
    first_result,
    leaves,
    results_path,
    search_ids,
)
from casebench.key_record import record_keys
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.setup.checks import unreachable
from casebench.setup.key_question import given_keys, hold_located, preset
from casebench.setup.picker import interactive, pick, text
from casebench.targets.placeholders import VARIABLE, split_command

FIELDS = (*REQUIRED_FIELDS, "level")
# The menu's own marks around a field's path and value.
GUTTER_ROOM = "  »  … "


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


# RFC 9110 sections 11.6.2 and 11.7.2: the headers that carry credentials.
CREDENTIAL_HEADERS = {"authorization", "proxy-authorization"}


def _headers(values: tuple[str, ...]) -> dict[str, str]:
    """Headers as given, except a credential typed in place of the variable that holds it:
    casebench.yaml names a key, never holds one (decision 0043)."""
    headers = _pairs(values)
    for name, value in headers.items():
        if name.lower() in CREDENTIAL_HEADERS and not VARIABLE.search(value):
            raise click.BadParameter(
                f"{name} would write a key into casebench.yaml; give it as ${{NAME}}, such as "
                f"'{name}=Bearer ${{DOC_KEY}}', or pass --key-env NAME"
            )
    return headers


NOT_THERE = "\0none"
TYPED = "\0typed"


def _shown(value: Any, room: int) -> str:
    """A field's value on one line, cut to the room the terminal leaves for it."""
    flat = " ".join(str(value).split())
    return flat if len(flat) <= room else f"{flat[: max(room - 1, 0)]}…"


def _choose(
    label: str,
    given: str | None,
    suggestion: str | None,
    ask: bool,
    fields: list[tuple[str, Any]] | None = None,
) -> str | None:
    """A flag's answer, else the suggestion when not asking. Asked on a terminal, the fields
    of the real response are listed with their values to pick from (decision 0043); asked
    elsewhere, the JSONPath is typed."""
    if given is not None or not ask:
        return given if given is not None else suggestion
    if fields and interactive():
        width = shutil.get_terminal_size().columns
        choices = [
            (f"{path}  {_shown(value, width - len(path) - len(GUTTER_ROOM))}", path)
            for path, value in fields
        ]
        choices += [("none of these", NOT_THERE), ("type a JSONPath…", TYPED)]
        picked = pick(label, choices, suggestion if suggestion in dict(fields) else None)
        if picked == NOT_THERE:
            return None
        if picked != TYPED:
            return picked
    return click.prompt(label, default=suggestion or "", show_default=bool(suggestion)) or None


def live_call(call: Any, what: str) -> Any:
    """A refused request says why in the user's terms; a connection that fails propagates."""
    try:
        return call()
    except (httpx2.UnsupportedProtocol, httpx2.InvalidURL) as error:
        raise click.ClickException(
            f"the {what} has no full http:// or https:// URL to go to; give the API's root URL, "
            "or a variable that holds it, such as --base-url '${DOCS_URL}'"
        ) from error
    except httpx2.HTTPStatusError as error:
        status = error.response.status_code
        hint = (
            "it needs an API key, or the key it got is wrong"
            if status in (401, 403)
            else "check the paths and the search"
        )
        raise click.ClickException(f"the API answered {status} to the {what}: {hint}") from error


SAYS = {
    "citation": "how the corpus cites the document",
    "type": "what kind of document it is",
    "passage": "the passage the search matched",
}


def _results(
    response: Any, results_given: str | None, given: dict[str, str], ask: bool
) -> tuple[dict[str, Any], str] | None:
    """Where each result is and what it says about its document, which is what the judge
    sees to match a citation (decision 0037); None when the results carry only ids."""
    where = _choose(
        "JSONPath to each result in a search response (empty if results carry only ids)",
        results_given,
        results_path(response),
        ask,
    )
    if not where:
        return None
    item = first_result(response, where)
    inside = leaves(item) if item is not None else None
    id_path = _choose("Which field of a result is its id?", given.get("id"), None, ask, inside)
    if not id_path:
        raise click.ClickException("no document id found in the search result; check the path")
    fields = {"id": id_path}
    for name, says in SAYS.items():
        path = _choose(f"Which field is {says}?", given.get(name), None, ask, inside)
        if path:
            fields[name] = path
    found = read_results(response, where, fields)
    if not found:
        raise click.ClickException("no document id found in the search result; check the path")
    seen = [name for name in SAYS if getattr(found[0], name) is not None]
    missing = [name for name in SAYS if name not in seen]
    click.echo(
        f"to match a citation the judge sees each result's {', '.join(seen) or 'id alone'}"
        + (
            f"; missing: {', '.join(missing)}, which Casebench fills from the document where it can"
            if missing
            else ""
        )
    )
    return {"search_results": where, "result_fields": fields}, found[0].id


def _map(
    store: Any,
    probe: str,
    ids_given: str | None,
    fields_given: dict[str, str],
    ask: bool,
    results_given: str | None = None,
    result_fields_given: dict[str, str] | None = None,
    show: bool = True,
) -> dict[str, Any]:
    """One live search and one fetch; show them, suggest paths, let the user correct them.
    Returns the connector options they set."""
    results = live_call(lambda: store.search_raw(probe, 1), "search")
    if show:  # what a user checks the paths against; Quick start takes them as suggested
        click.echo(f"search for {probe!r} returned:")
        for line in describe(results):
            click.echo(f"  {line}")
    # Ids given alone keep the results undescribed, as before.
    ids_only = ids_given is not None and results_given is None
    described = (
        None if ids_only else _results(results, results_given, result_fields_given or {}, ask)
    )
    if described is not None:
        options, first_id = described
    else:
        ids_path = _choose(
            "JSONPath to the ids in a search result", ids_given, search_ids(results), ask
        )
        if not ids_path or not every(ids_path, results):
            raise click.ClickException("no document id found in the search result; check the path")
        options, first_id = {"search_ids": ids_path}, str(every(ids_path, results)[0])
    document = live_call(lambda: store.fetch_raw(first_id), f"fetch of document {first_id}")
    if show:
        click.echo(f"document {first_id} returned:")
        for line in describe(document):
            click.echo(f"  {line}")
    suggested = document_fields(document, first_id)
    found_fields = leaves(document)
    fields = {}
    for name in FIELDS:
        asked = f"Which field of the document is its {name}?"
        path = _choose(asked, fields_given.get(name), suggested.get(name), ask, found_fields)
        if path:
            fields[name] = path
    mapped = record_fields(document, fields)
    missing = [name for name in REQUIRED_FIELDS if name not in mapped]
    click.echo("missing: " + ", ".join(missing) if missing else "every required field found")
    return options | {"fields": fields}


def valid_name(name: str | None) -> str | None:
    """A --name as casebench.yaml takes it, checked before anything is searched (0045)."""
    if name is not None and not re.fullmatch(NAME, name):
        raise click.BadParameter(
            f"{name!r} is not a name casebench.yaml takes: use lowercase letters, digits and "
            "hyphens, such as frontier-legal",
            param_hint="--name",
        )
    return name


def _save(config: Path, block: dict[str, Any], ask: bool, name: str | None = None) -> None:
    """Add the block under its name: the one given, or one made from the store."""
    name = name or name_for(block, taken_names(config))
    if ask and not click.confirm(f"add this corpus to {config} as {name}?", default=True):
        raise click.Abort()
    try:
        click.echo(write_corpus(config, name, block))
    except ConfigHasCorpus as error:
        raise click.ClickException(str(error)) from error


def codes(given: tuple[str, ...]) -> list[str]:
    """The jurisdictions given, as codes; an unknown one stops the command."""
    try:
        return [code(value) for value in given]
    except UnknownJurisdiction as error:
        raise click.BadParameter(str(error), param_hint="--jurisdiction") from error


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
    results: str | None = None,
    result_fields: tuple[str, ...] = (),
    jurisdictions: list[str] | None = None,
    ask: bool = True,
    show: bool = True,
    search_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask for what was not given, make one live search and fetch, and return the corpus block.
    `show` prints the responses the paths are suggested from."""
    base_url = _ask(
        base_url, "the document API's root URL, such as https://api.example.com/v1", ask
    )
    search_path = _ask(search_path, "the path that searches, under that URL, such as /search", ask)
    fetch_path = _ask(
        fetch_path,
        "the path that returns one document, with {id} where its id goes, such as /documents/{id}",
        ask,
    )
    options = http_options(
        base_url,
        search_path,
        query_param,
        fetch_path,
        headers,
        key_env,
        key_header_name,
        search_body,
    )
    probe = _ask(probe, "a search that finds at least one document", ask)
    store = connector("http", options)
    options |= _map(
        store, probe, ids_path, _pairs(fields), ask, results, _pairs(result_fields), show
    )
    # The search it was added with is the one `casebench check` runs (decision 0044).
    return {**corpus_block("http", options, jurisdictions), "probe": probe}


def _body(given: str | None) -> dict[str, Any] | None:
    if given is None:
        return None
    try:
        body = json.loads(given)
    except json.JSONDecodeError as error:
        raise click.BadParameter(f"not JSON: {error}", param_hint="--search-body") from error
    if not isinstance(body, dict):
        raise click.BadParameter(
            'a JSON object, such as {"query": "{text}"}', param_hint="--search-body"
        )
    return body


def key_names(base_url: str, headers: tuple[str, ...], key_env: str | None) -> set[str]:
    """Every variable the base URL and the headers name, and the key's own."""
    named = set(VARIABLE.findall(" ".join([base_url, *_pairs(headers).values()])))
    return named | {key_env} if key_env else named


def http_options(
    base_url: str,
    search_path: str,
    query_param: str,
    fetch_path: str,
    headers: tuple[str, ...],
    key_env: str | None,
    key_header_name: str,
    search_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The connector's options, with each key named, never given; every key they name must be
    set in the shell or read from a .env file already. A search body makes the search a POST."""
    if "{id}" not in fetch_path:
        raise click.BadParameter(f"{fetch_path!r} has no {{id}} for the document's id")
    sent = _headers(headers) | key_header(key_env or None, key_header_name)
    named = " ".join([base_url, *sent.values()])
    unset = sorted(n for n in set(VARIABLE.findall(named)) if not keys.get(n))
    if unset:
        raise click.ClickException(
            f"{', '.join(unset)} is set neither in this shell nor in any .env file here; "
            f"export it, or pass --key {unset[0]}=FILE"
        )
    searched: dict[str, Any] = (
        {"search_body": search_body}
        if search_body is not None
        else {"search_params": {query_param: "{text}"}}
    )
    return {
        "base_url": base_url,
        "headers": sent,
        "search_path": search_path,
        **searched,
        "fetch_path": fetch_path,
    }


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
    results: str | None = None,
    result_fields: tuple[str, ...] = (),
    jurisdictions: list[str] | None = None,
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
        options |= _map(store, probe, ids_path, _pairs(fields), ask, results, _pairs(result_fields))
    finally:
        store.close()
    return {**corpus_block("mcp", options, jurisdictions), "probe": probe}


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
    click.option("--results", help="JSONPath to each result in a search response."),
    click.option(
        "--result-field",
        "result_fields",
        multiple=True,
        help="NAME=JSONPath inside one result, for id, citation, type or passage.",
    ),
    click.option(
        "--jurisdiction",
        "jurisdictions",
        multiple=True,
        help="A jurisdiction the store covers, such as NO or US-CA; give it once for each.",
    ),
    click.option(
        "--name",
        callback=lambda _context, _option, value: valid_name(value),
        help="The corpus's name in casebench.yaml, such as frontier-legal; made from the store "
        "if not.",
    ),
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
@click.option(
    "--base-url",
    help="The API's root URL, such as https://api.example.com/v1, or a variable that holds it, "
    "such as '${DOCS_URL}'.",
)
@click.option("--search-path", help="Such as /search.")
@click.option("--query-param", default="q", show_default=True)
@click.option(
    "--search-body",
    help="For an API that searches by POST: its JSON body, with {text} where the words go, "
    'such as \'{"query": "{text}", "limit": "{limit}"}\'.',
)
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
@click.option(
    "--key",
    "key_files",
    multiple=True,
    metavar="NAME=FILE",
    help="The .env file a key is read from, relative to the config; found by name if not.",
)
@common
def http(
    base_url: str | None,
    search_path: str | None,
    query_param: str,
    search_body: str | None,
    fetch_path: str | None,
    key_env: str | None,
    key_header: str,
    headers: tuple[str, ...],
    config_path: Path,
    probe: str | None,
    ids_path: str | None,
    fields: tuple[str, ...],
    results: str | None,
    result_fields: tuple[str, ...],
    jurisdictions: tuple[str, ...],
    name: str | None,
    yes: bool,
    key_files: tuple[str, ...],
) -> None:
    """A document API reached over HTTP."""
    project = config_path.resolve().parent
    preset(given_keys(key_files, project))
    if not headers and key_env is None and not yes:
        key_env = text(
            "the environment variable that holds its API key (leave empty if it needs none)",
            default="",
            flag="--key-env NAME",
        )
    found = hold_located(key_names(base_url or "", headers, key_env), project)
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
        results=results,
        result_fields=result_fields,
        jurisdictions=codes(jurisdictions),
        ask=not yes,
        search_body=_body(search_body),
    )
    _save(config_path, block, not yes, name)
    for key, file in record_keys(config_path, found).items():
        click.echo(f"key {key}: read from {file}, by name; its value is not written")


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
    results: str | None,
    result_fields: tuple[str, ...],
    jurisdictions: tuple[str, ...],
    name: str | None,
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
        results=results,
        result_fields=result_fields,
        jurisdictions=codes(jurisdictions),
        ask=not yes,
    )
    _save(config_path, block, not yes, name)


@add.command()
@click.argument("given", metavar="FILE_OR_ID")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option(
    "--jurisdiction",
    "jurisdictions",
    multiple=True,
    help="Cover only these jurisdictions, instead of the profile's.",
)
@click.option(
    "--name",
    callback=lambda _context, _option, value: valid_name(value),
    help="The corpus's name in casebench.yaml; the profile's id if not.",
)
def profile(
    given: str, config_path: Path, jurisdictions: tuple[str, ...], name: str | None
) -> None:
    """A store described by a provider's profile: a file, or a bundled profile's id. Nothing
    is asked; one live search and fetch prove it works with your key."""
    if config_path.is_file():
        # The keys `keys:` names are read from their .env files, as for every command (0043).
        load_config(config_path)
    try:
        path, recorded = resolve(given)
        block, notes = profile_block(path, codes(jurisdictions), recorded)
    except ProfileProblem as error:
        raise click.ClickException(str(error)) from error
    except Exception as error:
        if unreachable(error):
            raise click.ClickException(
                f"the provider is not reachable from here; run this where it is: {error}"
            ) from error
        raise
    for note in notes:
        click.echo(note)
    _save(config_path, block, ask=False, name=name)
