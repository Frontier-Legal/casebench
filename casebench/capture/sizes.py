"""Measure what a tool returned, in characters, without keeping the content."""

import json
from typing import Any


def content_size(content: Any) -> int:
    """Characters of text, or of the JSON a structured result serialises to."""
    if isinstance(content, str):
        return len(content)
    return len(json.dumps(content, ensure_ascii=False))
