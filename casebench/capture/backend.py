"""Read a backend route's document ids by the JSONPath its config names, or from the path."""

import re
from typing import Any
from urllib.parse import unquote, urlsplit

from jsonpath_ng.ext.parser import parse as jsonpath

from casebench.capture.proxy.routes import Route
from casebench.capture.step import NO_DIAGNOSTIC, HttpExchange, Step, StepKind


def _ids(expression: str | None, document: Any) -> list[str]:
    if expression is None or document is None:
        return []
    return [str(match.value) for match in jsonpath(expression).find(document)]


def fetched(route: Route, url: str) -> str | None:
    """The id a request reads, when its path ends as the route's `fetch_path` does."""
    if route.fetch_path is None or "{id}" not in route.fetch_path:
        return None
    before, _, after = route.fetch_path.partition("{id}")
    pattern = re.escape(before) + r"([^/]+)" + re.escape(after) + "$"
    found = re.search(pattern, urlsplit(url).path)
    return unquote(found.group(1)) if found else None


def backend_step(exchange: HttpExchange, route: Route) -> Step:
    """One retrieval, rerank or document fetch; without ids found, it says so."""
    document_id = fetched(route, exchange.url)
    if document_id is not None:
        kind, ids_in, ids_out = StepKind.DOCUMENT, [], [document_id]
    else:
        kind = StepKind(route.step)
        ids_out = _ids(route.doc_ids, exchange.response_body)
        ids_in = _ids(route.doc_ids_in, exchange.request_body)
    return Step(
        kind=kind,
        name=route.name,
        doc_ids_in=ids_in,
        doc_ids_out=ids_out,
        started=exchange.started,
        ended=exchange.ended,
        duration_ms=exchange.duration_ms,
        note=None if ids_out else NO_DIAGNOSTIC,
    )
