"""Find the passage of a document that shares the most words with what was searched for."""

import re

WORD = re.compile(r"\w+")
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def words(text: str) -> set[str]:
    return set(WORD.findall(text.casefold()))


def _units(text: str) -> list[str]:
    """Paragraphs where the text has them, else lines; one unit when it has neither."""
    for split in (PARAGRAPH_BREAK.split, str.splitlines):
        parts = [part.strip() for part in split(text) if part.strip()]
        if len(parts) > 1:
            return parts
    return [text.strip()]


def _shortest_stretch(text: str, wanted: set[str]) -> str:
    """The shortest stretch of the text holding every wanted word it holds at all, so a text
    with no breaks is never shown whole for a few of its words (decision 0037)."""
    tokens = [(m.group().casefold(), m.start(), m.end()) for m in WORD.finditer(text)]
    needed = wanted & {word for word, _, _ in tokens}
    if not needed:
        return text.strip()
    counts: dict[str, int] = {}
    held, left, best = 0, 0, (0, len(text))
    for word, _, end in tokens:
        if word in needed:
            counts[word] = counts.get(word, 0) + 1
            held += counts[word] == 1
        while held == len(needed):
            first, start, _ = tokens[left]
            if end - start < best[1] - best[0]:
                best = (start, end)
            if first in needed:
                counts[first] -= 1
                held -= counts[first] == 0
            left += 1
    return text[best[0] : best[1]]


def best_passage(text: str, query: str) -> str | None:
    """The first paragraph, else line, with the most of the query's words; for a text with
    neither, the shortest stretch holding them. None for an empty text."""
    if not text.strip():
        return None
    wanted = words(query)
    units = _units(text)
    if len(units) == 1:
        return _shortest_stretch(units[0], wanted)
    return max(units, key=lambda unit: len(wanted & words(unit)))
