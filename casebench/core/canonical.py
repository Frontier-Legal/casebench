"""Canonical JSON, so the same record always hashes the same."""

import hashlib
import json
from collections.abc import Iterable
from typing import Any


def canonical_json(value: Any) -> str:
    """Keys sorted, no insignificant whitespace, non-ASCII kept as UTF-8."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(lines: Iterable[str]) -> str:
    """SHA-256 over the lines in order, each followed by a newline."""
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"
