"""Connect a document API or MCP server from the workbench, each field picked from real values.

One search, then one fetch once a result's id is picked, as `casebench corpus add` maps a store
at a terminal (decisions 0043, 0065).
"""

from dataclasses import dataclass, field
from typing import Any

import click

from casebench.corpus.add import corpus_block
from casebench.corpus.add_cli import connector, http_options, live_call
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
from casebench.targets.placeholders import split_command


@dataclass
class Picked:
    """What a person has picked so far; empty maps mean not picked yet."""

    probe: str
    jurisdictions: list[str] = field(default_factory=list)
    result_fields: dict[str, str] = field(default_factory=dict)
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Looked:
    """What the search and fetch showed: the fields to pick from, with their values, and the
    corpus block once a document was fetched."""

    results: str | None = None
    result_choices: list[tuple[str, Any]] = field(default_factory=list)
    document_choices: list[tuple[str, Any]] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    block: dict[str, Any] | None = None


def api_options(
    base_url: str,
    search_path: str,
    fetch_path: str,
    query_param: str = "q",
    key_env: str | None = None,
    key_header: str = "Authorization",
) -> dict[str, Any]:
    """A document API's connector options, its key named and never given."""
    return http_options(base_url, search_path, query_param, fetch_path, (), key_env, key_header)


def reach(command: str | None, url: str | None) -> dict[str, Any]:
    """How the MCP server is reached: a command that starts it, or its URL."""
    if bool(command) == bool(url):
        raise click.UsageError("give the command that starts the MCP server, or its URL")
    return {"command": split_command(command)} if command else {"url": url}


def tools(options: dict[str, Any]) -> list[tuple[str, str]]:
    """The MCP server's tools, by name and description, to pick search and fetch from."""
    store = connector("mcp", options)
    try:
        return [(name, description) for name, description, _ in store.tools()]
    finally:
        store.close()


def mcp_options(
    reached: dict[str, Any], search_tool: str, search_arg: str, fetch_tool: str, fetch_arg: str
) -> dict[str, Any]:
    return reached | {
        "search_tool": search_tool,
        "search_arguments": {search_arg: "{text}"},
        "fetch_tool": fetch_tool,
        "fetch_arguments": {fetch_arg: "{id}"},
    }


def look(kind: str, options: dict[str, Any], picked: Picked) -> Looked:
    """A search result's id is never guessed: until it is picked, only the search is made.
    Then one document is fetched, and its id, text and date suggested from their values."""
    store = connector(kind, options)
    try:
        return _look(store, kind, dict(options), picked)
    finally:
        closing = getattr(store, "close", None)
        if closing is not None:
            closing()


def _look(store: Any, kind: str, options: dict[str, Any], picked: Picked) -> Looked:
    response = live_call(lambda: store.search_raw(picked.probe, 1), "search")
    looked = Looked(results=results_path(response))
    if looked.results is not None:
        item = first_result(response, looked.results)
        looked.result_choices = leaves(item) if item is not None else []
        if not picked.result_fields.get("id"):
            return looked
        found = read_results(response, looked.results, picked.result_fields)
        if not found:
            raise click.ClickException("the field picked as the id is empty in the search result")
        first_id = found[0].id
        options |= {"search_results": looked.results, "result_fields": picked.result_fields}
    else:
        ids = search_ids(response)
        if ids is None or not every(ids, response):
            raise click.ClickException(
                f"the search for {picked.probe!r} found no document; try a search that does"
            )
        first_id = str(every(ids, response)[0])
        options |= {"search_ids": ids}
    document = live_call(lambda: store.fetch_raw(first_id), f"fetch of document {first_id}")
    looked.document_choices = leaves(document)
    looked.fields = picked.fields or document_fields(document, first_id)
    mapped = record_fields(document, looked.fields)
    looked.missing = [name for name in REQUIRED_FIELDS if name not in mapped]
    options |= {"fields": looked.fields}
    # The search it was added with is the one `casebench check` runs (decision 0044).
    looked.block = {**corpus_block(kind, options, picked.jurisdictions), "probe": picked.probe}
    return looked
