"""Read a matching prompt as a fake judge does: each citation with its candidates."""

import json
from collections.abc import Callable
from typing import Any


def asked(user: str) -> list[dict[str, Any]]:
    """Each citation of the prompt: `citation` (its number), `as_written` and `candidates`."""
    return json.loads(user.split("Citations:\n", 1)[1])


def picks(user: str, pick: Callable[[str, list[dict[str, Any]]], str | None]) -> list[dict]:
    """The reply a judge gives when `pick` names the document for each citation, or None."""
    return [
        {
            "citation": item["citation"],
            "document_id": pick(item["as_written"], item["candidates"]),
            "reason": "picked",
        }
        for item in asked(user)
    ]
