"""The corpus question in `casebench init`: bundled profiles by name, another store, or not now."""

from typing import Any

import click

from casebench.corpus.add import name_for
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


AGAIN = "Connect another source? (type to filter)"
DONE = ("that's all", "none")


def choices(added: frozenset[str] = frozenset()) -> tuple[list[tuple[str, str]], str | None]:
    """Bundled profiles by name and nothing else, then the other ways; a profile already
    added is not offered again, and after the first source "not now" becomes "that's all".
    The cursor starts on the first profile whose key is set here, and on nothing else
    (decision 0033)."""
    profiles = [item for item in bundled() if item.id not in added]
    listed = [(_title(item), f"{PROFILE}{item.id}") for item in profiles]
    found = next((f"{PROFILE}{item.id}" for item in profiles if item.key_found), None)
    others = OTHERS if not added else [*OTHERS[:-1], DONE]
    return [*listed, *others], found


def ask(added: frozenset[str] = frozenset(), again: bool = False) -> str:
    """`folder`, `http`, `mcp`, `none`, or `profile:<id>`."""
    listed, found = choices(added)
    return pick(AGAIN if again else QUESTION, listed, default=found)


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


def _one(where: str, folder: str | None) -> tuple[dict[str, Any] | None, list[str], bool]:
    """One source: its block, what to tell the user, and whether a live check already ran."""
    if where.startswith(PROFILE):
        block, notes = from_profile(where.removeprefix(PROFILE))
        return block, notes, True
    if where == "folder":
        path = folder if folder is not None else click.prompt("the folder")
        return {"connector": "folder", "options": {"path": path}}, [], False
    block, notes = from_store(where)
    return block, notes, True


class Sources:
    """The corpora init has added so far, each under a name of its own (decision 0036)."""

    def __init__(self) -> None:
        self.corpora: dict[str, dict[str, Any]] = {}
        self.checked: set[str] = set()

    def add(self, block: dict[str, Any] | None, checked: bool) -> None:
        if block is None:
            return
        name = name_for(block, set(self.corpora))
        self.corpora[name] = block
        if checked:
            self.checked.add(name)


def corpus_for_init(
    kind: str | None, folder: str | None, profiles: tuple[str, ...]
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    """Every corpus init sets up, by name, and the names whose live check already ran. With
    flags, the sources they name; without, the question again after each source added."""
    if profiles and kind:
        raise click.UsageError("give --profile or --corpus, not both")
    sources = Sources()
    if profiles or kind:
        for given in profiles:
            block, notes = from_profile(given)
            _echo(notes)
            sources.add(block, True)
        if kind == "none":
            click.echo(LATER)
        elif kind:
            block, notes, checked = _one(kind, folder)
            _echo(notes)
            sources.add(block, checked)
        return sources.corpora, sources.checked
    added: set[str] = set()
    while (where := ask(frozenset(added), again=bool(added))) != "none":
        if where.startswith(PROFILE):
            added.add(where.removeprefix(PROFILE))
        else:
            added.add(where)
        block, notes, checked = _one(where, folder)
        _echo(notes)
        sources.add(block, checked)
    if not sources.corpora:
        click.echo(LATER)
    return sources.corpora, sources.checked


def _echo(notes: list[str]) -> None:
    for note in notes:
        click.echo(note)
