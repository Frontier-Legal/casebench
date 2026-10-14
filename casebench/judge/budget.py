"""Split a judge's work into prompts that fit its model's context window."""

from collections.abc import Callable
from typing import TypeVar

Item = TypeVar("Item")

# OpenAI's published rule of thumb for English text; other languages differ (decision 0028).
CHARACTERS_PER_TOKEN = 4


def tokens(characters: int) -> int:
    return characters // CHARACTERS_PER_TOKEN


def batches(
    items: list[Item], size: Callable[[Item], int], fixed: int, window: int | None
) -> list[list[Item]]:
    """One batch unless the prompt, `fixed` characters plus each item's, would exceed `window`
    tokens; then as few batches as fit, in order. An item too large alone goes alone
    (decision 0037)."""
    if window is None or not items:
        return [items] if items else []
    out: list[list[Item]] = [[]]
    used = fixed
    for item in items:
        needed = size(item)
        if out[-1] and tokens(used + needed) > window:
            out.append([])
            used = fixed
        out[-1].append(item)
        used += needed
    return out
