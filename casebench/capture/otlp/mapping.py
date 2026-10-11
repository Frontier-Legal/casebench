"""Turn spans in the GenAI or OpenInference conventions into steps (decision 0023)."""

import json
import re
from typing import Any

from casebench.capture.otlp.decode import RawSpan
from casebench.capture.step import NO_DIAGNOSTIC, Step, StepKind

LLM_OPERATIONS = {"chat", "text_completion", "generate_content"}


def _indexed_ids(attributes: dict[str, Any], prefix: str) -> list[str]:
    """OpenInference flattens lists: `<prefix>.0.document.id`, `<prefix>.1.document.id`."""
    pattern = re.compile(rf"^{re.escape(prefix)}\.(\d+)\.document\.id$")
    found = sorted(
        (int(m.group(1)), str(v)) for k, v in attributes.items() if (m := pattern.match(k))
    )
    return [value for _, value in found]


def _documents(value: Any) -> list[str]:
    """`gen_ai.retrieval.documents`: a list of objects with `id`, possibly sent as JSON text."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    return [str(item["id"]) for item in value or [] if isinstance(item, dict) and "id" in item]


def _kind(attributes: dict[str, Any]) -> StepKind | None:
    operation = attributes.get("gen_ai.operation.name")
    span_kind = str(attributes.get("openinference.span.kind", "")).upper()
    if operation in LLM_OPERATIONS or span_kind == "LLM":
        return StepKind.LLM
    if operation == "execute_tool" or span_kind == "TOOL":
        return StepKind.TOOL
    if operation == "retrieval" or span_kind == "RETRIEVER":
        return StepKind.RETRIEVAL
    if (
        operation == "rerank"
        or span_kind == "RERANKER"
        or "casebench.rerank.output_ids" in attributes
    ):
        return StepKind.RERANK
    return None


def _ids(kind: StepKind, a: dict[str, Any]) -> tuple[list[str], list[str]]:
    if kind is StepKind.RETRIEVAL:
        return [], _documents(a.get("gen_ai.retrieval.documents")) or _indexed_ids(
            a, "retrieval.documents"
        )
    if kind is StepKind.RERANK:
        ids_in = [str(i) for i in a.get("casebench.rerank.input_ids") or []]
        ids_out = [str(i) for i in a.get("casebench.rerank.output_ids") or []]
        return (
            ids_in or _indexed_ids(a, "reranker.input_documents"),
            ids_out or _indexed_ids(a, "reranker.output_documents"),
        )
    return [], []


def _int(value: Any) -> int | None:
    return int(value) if value is not None else None


def to_step(span: RawSpan) -> Step | None:
    a = span.attributes
    kind = _kind(a)
    if kind is None:
        return None
    ids_in, ids_out = _ids(kind, a)
    searching = kind in (StepKind.RETRIEVAL, StepKind.RERANK)
    return Step(
        kind=kind,
        name=a.get("gen_ai.tool.name") or a.get("tool.name") or span.name,
        provider=a.get("gen_ai.provider.name") or a.get("gen_ai.system") or a.get("llm.provider"),
        model=a.get("gen_ai.response.model")
        or a.get("gen_ai.request.model")
        or a.get("llm.model_name"),
        input_tokens=_int(a.get("gen_ai.usage.input_tokens", a.get("llm.token_count.prompt"))),
        output_tokens=_int(
            a.get("gen_ai.usage.output_tokens", a.get("llm.token_count.completion"))
        ),
        doc_ids_in=ids_in,
        doc_ids_out=ids_out,
        started=span.started,
        ended=span.ended,
        duration_ms=(span.ended - span.started) * 1000,
        note=NO_DIAGNOSTIC if searching and not ids_out else None,
    )


def without_duplicates(span_steps: list[Step], proxied: list[Step]) -> list[Step]:
    """A model call the proxy saw is kept from the proxy; the span describing it is dropped."""
    calls = [s for s in proxied if s.kind is StepKind.LLM and s.started is not None]

    def seen_by_proxy(step: Step) -> bool:
        if step.kind is not StepKind.LLM or step.started is None or step.ended is None:
            return False
        return any(step.started <= c.started <= step.ended for c in calls if c.started is not None)

    return [step for step in span_steps if not seen_by_proxy(step)]
