"""Generate a suite's cases deterministically from its id."""

import hashlib
from collections.abc import Callable, Sequence
from typing import TypeVar

from casebench.core.case import Case

Source = TypeVar("Source")


def rank(suite_id: str, source_key: str) -> str:
    """A source's place in a suite: SHA-256 of the suite id and the source's key.

    Python's `random` only promises the same `random()` sequence across versions, not
    the same `sample()`, so ranking by hash keeps a suite identical on every Python.
    """
    return hashlib.sha256(f"{suite_id}\n{source_key}".encode()).hexdigest()


def generate(
    suite_id: str,
    sources: Sequence[Source],
    build: Callable[[Source], Case],
    *,
    key: Callable[[Source], str],
    n: int | None = None,
) -> list[Case]:
    """Build cases from sources, sampled and ordered by the suite id.

    The same suite id and the same sources give the same cases in the same order,
    whatever order the sources arrive in.
    """
    keys = [key(source) for source in sources]
    if len(set(keys)) != len(keys):
        raise ValueError("two sources share a key")
    count = len(sources) if n is None else n
    if count > len(sources):
        raise ValueError(f"asked for {count} cases from {len(sources)} sources")
    ranked = sorted(sources, key=lambda source: rank(suite_id, key(source)))
    return [build(source) for source in ranked[:count]]
