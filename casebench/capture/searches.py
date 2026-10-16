"""Search stores whose API Casebench reads on its own, by the request's path (decision 0061).

A Python agent's call reaches the proxy through the follow path wherever it goes (0044). A
followed call that no route and no parser reads is matched against these APIs; a match becomes
a retrieval step with the ids the store returned. The ids are the store's own: a store that
keeps a document's corpus id in a payload field needs a route whose `doc_ids` reads that field.
"""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from jsonpath_ng.ext.parser import parse as jsonpath

from casebench.capture.step import NO_DIAGNOSTIC, HttpExchange, Step, StepKind


@dataclass(frozen=True)
class SearchApi:
    """A store's search API: the package its Python client ships in, the paths of a search,
    and where its reply holds the ids, tried in order."""

    name: str
    package: str
    path: re.Pattern[str]
    ids: tuple[str, ...]


# Qdrant's REST API, read on 2026-10-15: `points/search` replies with a list of points,
# `points/query` with `{points: [...]}`, and each batch form with one of those per search. Its
# Python client sends REST calls through httpx.
QDRANT = SearchApi(
    name="Qdrant",
    package="qdrant-client",
    path=re.compile(r"/collections/[^/]+/points/(search|query)(/batch)?$"),
    ids=(
        "$.result.points[*].id",
        "$.result[*].points[*].id",
        "$.result[*][*].id",
        "$.result[*].id",
    ),
)
SEARCH_APIS = (QDRANT,)


def _ids(expressions: tuple[str, ...], document: Any) -> list[str]:
    for expression in expressions:
        found = [str(match.value) for match in jsonpath(expression).find(document)]
        if found:
            return found
    return []


def search_step(exchange: HttpExchange) -> Step | None:
    """A retrieval step when the call is a search of a store whose API is known, else None."""
    path = urlsplit(exchange.url).path
    api = next((api for api in SEARCH_APIS if api.path.search(path)), None)
    if api is None or exchange.method.upper() != "POST":
        return None
    ids = _ids(api.ids, exchange.response_body) if exchange.status < 400 else []
    return Step(
        kind=StepKind.RETRIEVAL,
        name=f"{api.name} search",
        doc_ids_out=ids,
        started=exchange.started,
        ended=exchange.ended,
        duration_ms=exchange.duration_ms,
        note=None if ids else NO_DIAGNOSTIC,
    )
