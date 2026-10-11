"""Read a server-sent events stream into its JSON payloads."""

import json
from typing import Any


def parse_events(raw: bytes) -> list[Any]:
    """Each `data:` payload that is JSON, in order; `[DONE]` and comments are skipped."""
    events: list[Any] = []
    data: list[str] = []
    for line in [*raw.decode("utf-8", "replace").splitlines(), ""]:
        if line.startswith("data:"):
            data.append(line[len("data:") :].strip())
        elif line == "" and data:
            payload = "\n".join(data)
            data = []
            if payload == "[DONE]":
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
    return events
