"""Turn whatever a target returns into an answer with citations and documents."""

from collections.abc import Mapping
from typing import Any

from pydantic import Field

from casebench.core.model import FrozenRecord


class Answer(FrozenRecord):
    """A plain-text answer has no citations here; the judge lists them when it grades."""

    text: str
    citations: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)


def to_answer(value: Any) -> Answer:
    if isinstance(value, Answer):
        return value
    if isinstance(value, str):
        return Answer(text=value)
    if isinstance(value, Mapping):
        if "answer" not in value:
            raise ValueError("a target that returns a mapping must include 'answer'")
        return Answer(
            text=str(value["answer"]),
            citations=[str(c) for c in value.get("citations") or []],
            documents=[str(d) for d in value.get("documents") or []],
        )
    raise TypeError(f"a target returned {type(value).__name__}; expected a string or a mapping")
