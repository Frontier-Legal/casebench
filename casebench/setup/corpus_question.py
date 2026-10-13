"""The corpus question in `casebench init`: bundled profiles by name, another store, or not now."""

from typing import Any

import click

from casebench.corpus.add_cli import http_block, mcp_block
from casebench.corpus.bundled import Bundled, bundled, resolve
from casebench.corpus.from_profile import ProfileProblem, load_profile, profile_block
from casebench.setup.checks import Status, unreachable
from casebench.setup.picker import pick

QUESTION = (
    "Connect a source of court decisions? Casebench builds test cases from it "
    "and checks every citation against it (type to filter)"
)
PROFILE = "profile:"
OTHERS = [
    ("a folder of decisions on this machine", "folder"),
    ("another HTTP API (you give its address and paths)", "http"),
    ("another MCP server (you give its command or URL)", "mcp"),
    ("not now: I'll bring lawyer-written cases", "none"),
]
LATER = "corpus   none yet: citation checks wait until one is added with `casebench corpus add`"


def _title(item: Bundled) -> str:
    places = f"  ({', '.join(item.profile.jurisdictions)})" if item.profile.jurisdictions else ""
    return f"{item.profile.name}{places}{'  · key found' if item.key_found else ''}"


def choices() -> tuple[list[tuple[str, str]], str | None]:
    """Bundled profiles by name and nothing else, then the other ways. The cursor starts on
    the first profile whose key is set here, and on nothing else (decision 0033)."""
    profiles = bundled()
    listed = [(_title(item), f"{PROFILE}{item.id}") for item in profiles]
    found = next((f"{PROFILE}{item.id}" for item in profiles if item.key_found), None)
    return [*listed, *OTHERS], found


def ask() -> str:
    """`folder`, `http`, `mcp`, `none`, or `profile:<id>`."""
    listed, found = choices()
    return pick(QUESTION, listed, default=found)


def from_store(kind: str) -> tuple[dict[str, Any] | None, list[str]]:
    """An HTTP or MCP store is described from one live search and fetch (decision 0025).
    One that refuses or cannot be reached is left out, with what to do about it."""
    later = f"run `casebench corpus add {kind}` once that is fixed"
    try:
        block = http_block() if kind == "http" else mcp_block()
    except click.ClickException as error:
        return None, [f"corpus   not added: {error.format_message()}; {later}"]
    except Exception as error:
        if unreachable(error):
            return None, [f"corpus   {Status.UNREACHABLE.value}; {later}, where it is reachable"]
        raise
    return block, ["corpus   added after one live search and fetch"]


def from_profile(given: str) -> tuple[dict[str, Any] | None, list[str]]:
    """A profile that cannot be found or read stops init before anything is written. One whose
    live check fails here is left out, like any corpus that is not reachable from here."""
    try:
        path, recorded = resolve(given)
        load_profile(path)
    except ProfileProblem as error:
        raise click.ClickException(str(error)) from error
    later = f"run `casebench corpus add profile {given}` once that is fixed"
    try:
        block, notes = profile_block(path, recorded=recorded)
    except ProfileProblem as error:
        return None, [f"corpus   not added: {error}; {later}"]
    except Exception as error:
        if unreachable(error):
            return None, [f"corpus   {Status.UNREACHABLE.value}; {later}, where it is reachable"]
        raise
    return block, [f"corpus   {note}" for note in notes]


def corpus_for_init(
    kind: str | None, folder: str | None, profile: str | None
) -> tuple[dict[str, Any] | None, list[str], str]:
    """The corpus block, what to tell the user, and which way was taken."""
    if profile and kind:
        raise click.UsageError("give --profile or --corpus, not both")
    where = f"{PROFILE}{profile}" if profile else kind or ask()
    if where.startswith(PROFILE):
        block, notes = from_profile(where.removeprefix(PROFILE))
        return block, notes, "profile"
    if where == "folder":
        path = folder if folder is not None else click.prompt("the folder")
        return {"connector": "folder", "options": {"path": path}}, [], where
    if where in ("http", "mcp"):
        block, notes = from_store(where)
        return block, notes, where
    return None, [LATER], where
