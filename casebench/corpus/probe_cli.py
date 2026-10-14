"""`casebench corpus probe`: one live search or fetch, printed for whoever maps its fields."""

import json
from pathlib import Path
from typing import Any

import click

from casebench.config import DEFAULT_CONFIG
from casebench.corpus.add_cli import connector, http_options, key_names, live_call
from casebench.setup.key_question import given_keys, hold_located, preset


@click.group()
def probe() -> None:
    """Show what a document store answers, so its fields can be mapped by flags (0044)."""


@probe.command()
@click.option("--base-url", required=True, help="The API's root URL.")
@click.option("--search-path", default="/search", show_default=True)
@click.option("--query-param", default="q", show_default=True)
@click.option("--fetch-path", default="/documents/{id}", show_default=True)
@click.option("--key-env", help="The variable that holds the API key, found by name.")
@click.option("--key-header", default="Authorization", show_default=True)
@click.option("--header", "headers", multiple=True, help="NAME=VALUE; ${VAR} names a key.")
@click.option("--key", "key_files", multiple=True, metavar="NAME=FILE")
@click.option("--query", help="Search for this and print the response.")
@click.option("--fetch", "document_id", help="Fetch this document and print it.")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
    help="Its folder is the project whose .env files hold the key.",
)
def http(
    base_url: str,
    search_path: str,
    query_param: str,
    fetch_path: str,
    key_env: str | None,
    key_header: str,
    headers: tuple[str, ...],
    key_files: tuple[str, ...],
    query: str | None,
    document_id: str | None,
    config_path: Path,
) -> None:
    """One search, one fetch, or both, printed as JSON with the key used by name and never
    shown. Map the fields with `casebench corpus add http` and its field flags after."""
    if query is None and document_id is None:
        raise click.UsageError("give --query to search, --fetch ID to read one document, or both")
    project = config_path.resolve().parent
    preset(given_keys(key_files, project))
    hold_located(key_names(headers, key_env), project)
    options = http_options(
        base_url, search_path, query_param, fetch_path, headers, key_env, key_header
    )
    store = connector("http", options)
    shown: dict[str, Any] = {}
    if query is not None:
        shown["search"] = {
            "query": query,
            "response": live_call(lambda: store.search_raw(query, 1), "search"),
        }
    if document_id is not None:
        fetched = live_call(
            lambda: store.fetch_raw(document_id), f"fetch of document {document_id}"
        )
        shown["document"] = {"id": document_id, "response": fetched}
    click.echo(json.dumps(shown, ensure_ascii=False, indent=2, default=str))
