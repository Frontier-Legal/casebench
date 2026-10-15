"""The keys Casebench calls services with, kept in its own memory and out of every output.

A key read from a .env file is held here, never set in the environment, so the agent and
every other child process start without it; a key the shell sets is read where it is
(decision 0043).
"""

import hashlib
import os
from collections import ChainMap
from collections.abc import Iterable, Mapping

# 8 hex characters of SHA-256: two different keys share them once in about four billion pairs.
FINGERPRINT_LENGTH = 8
# What a credential seen only in a header becomes in what a run writes (decision 0046).
HIDDEN = "[credential]"
# Shorter values are not hidden: replacing them would rewrite ordinary text.
SHORTEST_HIDDEN = 8

_held: dict[str, str] = {}
_named: set[str] = set()
_seen: set[str] = set()


def hold(name: str, value: str) -> None:
    """Keep a key read from a file for this process's own calls."""
    if value:
        _held[name] = value


def get(name: str) -> str | None:
    """The shell's value first, then one read from a .env file."""
    return os.environ.get(name) or _held.get(name) or None


def lookup() -> Mapping[str, str]:
    """Every variable `${NAME}` may name in a header: the shell's, then the keys held."""
    return ChainMap(dict(os.environ), _held)


def name(variable: str) -> None:
    """Treat a variable as a key: the config names it in a header or as a provider's key."""
    _named.add(variable)


def hide(value: str) -> None:
    """Keep out of what a run writes a credential a call carried, whatever variable it came
    from (decision 0046)."""
    if len(value) >= SHORTEST_HIDDEN:
        _seen.add(value)


def scrub(text: str, names: Iterable[str] = ()) -> str:
    """Text with the value of every held key, of each variable named here or before, replaced
    by `${NAME}`, and each credential a call carried by `[credential]`, so nothing written or
    shown holds a key."""
    for variable in {*_held, *_named, *names}:
        value = get(variable)
        if value:
            text = text.replace(value, f"${{{variable}}}")
    for value in sorted(_seen, key=len, reverse=True):
        text = text.replace(value, HIDDEN)
    return text


def fingerprint(value: str) -> str:
    """Enough to tell two keys apart and nothing of the key itself: the start of its
    SHA-256, a one-way hash (FIPS 180-4)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:FINGERPRINT_LENGTH]
