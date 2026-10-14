"""The corpus question in `casebench init`: bundled profiles by name, another store, or not now."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

from casebench.corpus.add import name_for
from casebench.corpus.add_cli import http_block, mcp_block
from casebench.corpus.bundled import Bundled, bundled, resolve
from casebench.corpus.from_profile import ProfileProblem, load_profile, profile_block
from casebench.setup import screen
from casebench.setup.checks import Status, unreachable
from casebench.setup.key_question import KeyFound, key_for, use
from casebench.setup.picker import interactive, pick, text

QUESTION = (
    "Connect a source of court decisions? Casebench builds test cases from it "
    "and checks every citation against it"
)
PROFILE = "profile:"
OTHERS = [
    ("a folder of decisions on this machine", "folder"),
    ("another HTTP API (you give its address and paths)", "http"),
    ("another MCP server (you give its command or URL)", "mcp"),
    ("not now: I'll bring lawyer-written cases", "none"),
]
LATER = "no corpus yet: citation checks wait until one is added with `casebench corpus add`"
AGAIN_HTTP = [
    ("change the address, the paths or the key", "again"),
    ("skip it for now", "skip"),
]


def _title(item: Bundled) -> str:
    places = f"  ({', '.join(item.profile.jurisdictions)})" if item.profile.jurisdictions else ""
    return f"{item.profile.name}{places}{'  · key found' if item.key_found else ''}"


AGAIN = "Connect another source?"
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


@dataclass
class Added:
    """One source's block, what to tell the user, whether its live check ran, and its key."""

    block: dict[str, Any] | None
    notes: list[str] = field(default_factory=list)
    checked: bool = False
    key: KeyFound | None = None


def http_store(root: Path, custom: bool) -> Added:
    """The address and paths asked, the key found in the shell or a .env file, then one live
    search and fetch; Quick start takes the suggested paths, Custom asks each. A failure says
    why and offers to change something or skip, without starting init again (decision 0043)."""
    later = "run `casebench corpus add http` once that is fixed"
    while True:
        base_url = text("the document API's root URL, such as https://api.example.com/v1")
        search_path = text("the path that searches, under that URL", default="/search")
        fetch_path = text("the path that returns one document", default="/documents/{id}")
        key = key_for(None, root, "corpus")
        if key is not None:
            use(key)
            screen.ok(f"key {key.said(root)}")
        probe = text("a search that finds at least one document")
        screen.line("one search and one fetch…")
        try:
            block = http_block(
                base_url=base_url,
                search_path=search_path,
                fetch_path=fetch_path,
                key_env=key.name if key else "",
                probe=probe,
                ask=True,  # which field is which is asked in both lanes; none is guessed (0043)
                show=custom,
            )
        except click.ClickException as error:
            reason = error.format_message()
        except Exception as error:
            if not unreachable(error):
                raise
            reason = f"{Status.UNREACHABLE.value}; run it where the API is reachable"
        else:
            screen.ok("one search and one fetch answered")
            return Added(block, [], True, key)
        screen.fail(reason)
        if not interactive() or pick("The corpus did not answer. What now?", AGAIN_HTTP) == "skip":
            return Added(None, [f"corpus   not added: {reason}; {later}"])


def from_store(kind: str) -> tuple[dict[str, Any] | None, list[str]]:
    """An MCP store is described from one live search and fetch (decision 0025). One that
    refuses or cannot be reached is left out, with what to do about it."""
    later = f"run `casebench corpus add {kind}` once that is fixed"
    try:
        block = mcp_block()
    except click.ClickException as error:
        return None, [f"corpus   not added: {error.format_message()}; {later}"]
    except Exception as error:
        if unreachable(error):
            return None, [f"corpus   {Status.UNREACHABLE.value}; {later}, where it is reachable"]
        raise
    return block, ["corpus   added after one live search and fetch"]


def from_profile(given: str, root: Path) -> Added:
    """A profile that cannot be found or read stops init before anything is written. Its key
    is found in the shell or a .env file first. One whose live check fails here is left out,
    like any corpus that is not reachable from here."""
    try:
        path, recorded = resolve(given)
        profile, _ = load_profile(path)
    except ProfileProblem as error:
        raise click.ClickException(str(error)) from error
    key = key_for(profile.key_env, root, profile.name) if profile.key_env else None
    if key is not None:
        use(key)
    later = f"run `casebench corpus add profile {given}` once that is fixed"
    try:
        block, notes = profile_block(path, recorded=recorded)
    except ProfileProblem as error:
        return Added(None, [f"corpus   not added: {error}; {later}"], key=key)
    except Exception as error:
        if unreachable(error):
            notes = [f"corpus   {Status.UNREACHABLE.value}; {later}, where it is reachable"]
            return Added(None, notes, key=key)
        raise
    return Added(block, [f"corpus   {note}" for note in notes], True, key)


def _one(where: str, folder: str | None, root: Path, custom: bool) -> Added:
    if where.startswith(PROFILE):
        return from_profile(where.removeprefix(PROFILE), root)
    if where == "folder":
        path = folder if folder is not None else text("the folder")
        return Added({"connector": "folder", "options": {"path": path}})
    if where == "http":
        return http_store(root, custom)
    block, notes = from_store(where)
    return Added(block, notes, True)


class Sources:
    """The corpora init has added so far, each under a name of its own (decision 0036), and
    the keys they are read with."""

    def __init__(self) -> None:
        self.corpora: dict[str, dict[str, Any]] = {}
        self.checked: set[str] = set()
        self.keys: list[KeyFound] = []
        self.missed = False

    def add(self, added: Added) -> None:
        for note in added.notes:
            said = note.removeprefix("corpus").strip()
            (screen.warn if said.startswith(("not added", "not reachable")) else screen.line)(said)
        if added.key is not None:
            self.keys.append(added.key)
        if added.block is None:
            self.missed = self.missed or bool(added.notes)
            return
        name = name_for(added.block, set(self.corpora))
        self.corpora[name] = added.block
        if added.checked:
            self.checked.add(name)


def corpus_for_init(
    kind: str | None,
    folder: str | None,
    profiles: tuple[str, ...],
    root: Path,
    custom: bool = True,
) -> Sources:
    """Every corpus init sets up, by name, the names whose live check already ran, and the
    keys found for them. With flags, the sources they name; without, the question again after
    each source added."""
    if profiles and kind:
        raise click.UsageError("give --profile or --corpus, not both")
    sources = Sources()
    if profiles or kind:
        for given in profiles:
            sources.add(from_profile(given, root))
        if kind == "none":
            screen.line(LATER)
        elif kind:
            sources.add(_one(kind, folder, root, custom))
        return sources
    added: set[str] = set()
    while (where := ask(frozenset(added), again=bool(added))) != "none":
        added.add(where.removeprefix(PROFILE) if where.startswith(PROFILE) else where)
        sources.add(_one(where, folder, root, custom))
    if not sources.corpora:
        screen.line(LATER)
    return sources
