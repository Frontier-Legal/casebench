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

_held: dict[str, str] = {}


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


def scrub(text: str, names: Iterable[str] = ()) -> str:
    """Text with the value of every held key, and of each variable named, replaced by
    `${NAME}`, so an error that echoes a request never shows the key."""
    for name in {*_held, *names}:
        value = get(name)
        if value:
            text = text.replace(value, f"${{{name}}}")
    return text


def fingerprint(value: str) -> str:
    """Enough to tell two keys apart and nothing of the key itself: the start of its
    SHA-256, a one-way hash (FIPS 180-4)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:FINGERPRINT_LENGTH]
