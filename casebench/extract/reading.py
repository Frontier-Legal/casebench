"""Turn one model's reply about a decision into items with spans located in its text."""

from dataclasses import dataclass, field
from typing import Any

from casebench.extract.prompt import OUTCOMES


@dataclass(frozen=True)
class Item:
    value: str
    quote: str
    span: tuple[int, int]

    def overlaps(self, other: "Item") -> bool:
        return self.span[0] < other.span[1] and other.span[0] < self.span[1]


@dataclass
class Reading:
    """What one model found, with only the items whose quote is really in the text."""

    outcome: Item | None = None
    statutes: list[Item] = field(default_factory=list)
    precedents: list[Item] = field(default_factory=list)
    facts: str = ""


def _locate(text: str, value: Any, quote: Any) -> Item | None:
    if not isinstance(value, str) or not isinstance(quote, str) or not quote.strip():
        return None
    start = text.find(quote.strip())
    if start < 0:
        return None
    return Item(value=value.strip(), quote=quote.strip(), span=(start, start + len(quote.strip())))


def read_reply(text: str, reply: Any) -> Reading:
    reading = Reading()
    if not isinstance(reply, dict):
        return reading
    outcome = reply.get("outcome") or {}
    if isinstance(outcome, dict) and outcome.get("label") in OUTCOMES:
        reading.outcome = _locate(text, outcome["label"], outcome.get("quote"))
    for name in ("statutes", "precedents"):
        items = [
            _locate(text, entry.get("citation"), entry.get("quote"))
            for entry in reply.get(name) or []
            if isinstance(entry, dict)
        ]
        setattr(reading, name, [item for item in items if item is not None])
    facts = reply.get("facts")
    reading.facts = facts.strip() if isinstance(facts, str) else ""
    return reading
