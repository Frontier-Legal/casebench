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
    GAP = "gap"


class HttpExchange(FrozenRecord):
    """One request and its response, as the recording proxy saw them.

    Auth headers are never recorded. A streamed response keeps its parsed events in
    `response_events`; times are seconds since the epoch.
    """

    method: str
    url: str
    request_body: Any = None
    status: int
    response_body: Any = None
    response_events: list[Any] | None = None
    route: str | None = None
    started: float | None = None
    ended: float | None = None
    duration_ms: float | None = None


NO_DIAGNOSTIC = "no diagnostic possible"


class ToolCall(FrozenRecord):
    """A tool call a model asked for."""

    id: str
    name: str
    arguments: Any = None


class ToolResult(FrozenRecord):
    """A tool result sent back to a model, by the id of the call it answers."""

    id: str
    size: int


class Step(FrozenRecord):
    """One thing an agent did, with the document ids that went in and came out."""

    kind: StepKind
    name: str | None = None
    provider: str | None = None
    model: str | None = None
    doc_ids_in: list[str] = Field(default_factory=list)
    doc_ids_out: list[str] = Field(default_factory=list)
    input_tokens: int | None = None
    output_tokens: int | None = None
    arguments: Any = None
    result_size: int | None = None
    requested_tools: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    started: float | None = None
    ended: float | None = None
    duration_ms: float | None = None
    note: str | None = None
