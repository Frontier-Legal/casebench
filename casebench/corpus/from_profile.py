"""Turn a profile file into a corpus block, after one live search and fetch with the user's key."""

import os
from pathlib import Path
from typing import Any

import httpx2
import yaml
from pydantic import ValidationError

from casebench.corpus.add import corpus_block
from casebench.corpus.profile import FORMAT, Metered, Profile
from casebench.corpus.record import REQUIRED_FIELDS
from casebench.formats.read import ignored_note, read
from casebench.formats.version import FormatVersion, UnreadableFormat
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.setup.checks import unreachable
from casebench.targets.placeholders import VARIABLE


class ProfileProblem(ValueError):
    """The profile cannot be used here: unreadable, a key not set, or its live check failed."""


def load_profile(path: Path) -> tuple[Profile, list[str]]:
    """The profile, and a note for each field a newer minor version added."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ProfileProblem(f"{path} cannot be read: {error}") from error
    if not isinstance(data, dict) or "format" not in data:
        raise UnreadableFormat(f"{path} names no format; a profile starts with {FORMAT}")
    declared = FormatVersion.parse(data["format"])
    try:
        profile, ignored = read(Profile, data, declared, FORMAT)
    except ValidationError as error:
        raise ProfileProblem(f"{path} is not a valid profile:\n{error}") from error
    notes = [ignored_note(str(path), declared, FORMAT, ignored)] if ignored else []
    return profile, notes


def _unset(profile: Profile) -> list[str]:
    named = set(VARIABLE.findall(str(profile.options)))
    if profile.key_env:
        named.add(profile.key_env)
    return sorted(name for name in named if not os.environ.get(name))


def _reason(error: BaseException) -> str:
    """The innermost error in words: an SDK reports a refusal inside nested groups."""
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    if isinstance(error, httpx2.HTTPStatusError):
        return f"it answered {error.response.status_code}"
    return str(error) or type(error).__name__


def _check(profile: Profile) -> str:
    """One search with the profile's probe and one fetch of what it found, through the
    connector the profile names. Returns the id that was fetched."""
    try:
        store: Any = registry.load(kind_named("connector"), profile.connector)(**profile.options)
        try:
            found = store.search(profile.probe, 1)
            if not found:
                raise ProfileProblem(f"the search {profile.probe!r} found no document")
            document = store.fetch(found[0])
        finally:
            close = getattr(store, "close", None)
            if close is not None:
                close()
    except ProfileProblem:
        raise
    except Exception as error:
        if unreachable(error):
            raise
        hint = f"; check that {profile.key_env} holds a valid key" if profile.key_env else ""
        raise ProfileProblem(
            f"{profile.name} refused the live check ({_reason(error)}){hint}"
        ) from error
    missing = [name for name in REQUIRED_FIELDS if document.get(name) in (None, "")]
    if missing:
        raise ProfileProblem(
            f"document {found[0]} came back without {', '.join(missing)}; "
            "the profile's field paths do not match what the provider returns"
        )
    return found[0]


def profile_block(
    path: Path, jurisdictions: list[str] | None = None, recorded: str | None = None
) -> tuple[dict[str, Any], list[str]]:
    """The corpus block for casebench.yaml, and what to tell the user. Nothing is returned
    unless the live check passed, so a broken profile fails before anything is written.
    `recorded` is what the block names as its profile: a bundled id, or the file's name."""
    profile, notes = load_profile(path)
    unset = _unset(profile)
    if unset:
        raise ProfileProblem(f"{', '.join(unset)} is not set in this shell; export it first")
    fetched = _check(profile)
    block = corpus_block(profile.connector, profile.options, jurisdictions or profile.jurisdictions)
    block["profile"] = recorded or path.name
    if profile.metered is not Metered.NONE:
        block["metered"] = profile.metered.value
    notes.append(f"{profile.name}: searched {profile.probe!r} and fetched document {fetched}")
    if profile.metered is not Metered.NONE:
        notes.append(
            f"{profile.name} charges per {profile.metered.value}: this check used one search and "
            f"one fetch, and Casebench keeps each {profile.metered.value} so it is paid once"
        )
    if profile.terms:
        notes.append(f"its terms: {profile.terms}")
    return block, notes
