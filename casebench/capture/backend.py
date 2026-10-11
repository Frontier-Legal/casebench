"""Read a backend route's document ids by the JSONPath its config names."""

from typing import Any

from jsonpath_ng.ext.parser import parse as jsonpath

from casebench.capture.proxy.routes import Route
from casebench.capture.step import NO_DIAGNOSTIC, HttpExchange, Step, StepKind


def _ids(expression: str | None, document: Any) -> list[str]:
    if expression is None or document is None:
        return []
    return [str(match.value) for match in jsonpath(expression).find(document)]


def backend_step(exchange: HttpExchange, route: Route) -> Step:
    """One retrieval or rerank step; without a JSONPath, or with no ids found, it says so."""
    ids_out = _ids(route.doc_ids, exchange.response_body)
    ids_in = _ids(route.doc_ids_in, exchange.request_body)
    return Step(
        kind=StepKind(route.step),
        name=route.name,
        doc_ids_in=ids_in,
        doc_ids_out=ids_out,
        started=exchange.started,
        ended=exchange.ended,
        duration_ms=exchange.duration_ms,
        note=None if ids_out else NO_DIAGNOSTIC,
    )
