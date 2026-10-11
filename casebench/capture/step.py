"""The normalised step model, and the HTTP exchange a capture parser reads."""

from enum import StrEnum
from typing import Any

from pydantic import Field

from casebench.core.model import FrozenRecord


class StepKind(StrEnum):
    LLM = "llm"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    RERANK = "rerank"
    DOCUMENT = "document"


class HttpExchange(FrozenRecord):
    """One request and its response, as the recording proxy saw them. Auth headers are
    never recorded."""

    method: str
    url: str
    request_body: Any = None
    status: int
    response_body: Any = None
    duration_ms: float | None = None


class Step(FrozenRecord):
    """One thing an agent did, with the document ids that went in and came out."""

    kind: StepKind
    name: str | None = None
    model: str | None = None
    doc_ids_in: list[str] = Field(default_factory=list)
    doc_ids_out: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: float | None = None
