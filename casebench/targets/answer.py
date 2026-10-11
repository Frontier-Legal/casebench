"""Turn whatever a target returns into an answer with citations and documents."""

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import Field

from casebench.core.model import FrozenRecord

CitationParser = Callable[[str], list[str]]


class Answer(FrozenRecord):
    text: str
    citations: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)


def to_answer(value: Any, parse_citations: CitationParser | None = None) -> Answer:
    """A string has its citations parsed by the adapter; a mapping brings its own."""
    if isinstance(value, Answer):
        return value
    if isinstance(value, str):
        return Answer(text=value, citations=parse_citations(value) if parse_citations else [])
    if isinstance(value, Mapping):
        if "answer" not in value:
            raise ValueError("a target that returns a mapping must include 'answer'")
        text = str(value["answer"])
        citations = value.get("citations")
        return Answer(
            text=text,
            citations=[str(c) for c in citations]
            if citations is not None
            else (parse_citations(text) if parse_citations else []),
            documents=[str(d) for d in value.get("documents") or []],
        )
    raise TypeError(f"a target returned {type(value).__name__}; expected a string or a mapping")
