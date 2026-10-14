"""The corpus connector contract: where documents come from, never how to read them."""

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from casebench.corpus.results import SearchResult


class ListingNotSupported(NotImplementedError):
    """The store cannot enumerate its documents; sample it through searches instead."""


class FiltersNotSupported(NotImplementedError):
    """The config sets search filters for a connector that cannot apply them."""


@runtime_checkable
class CorpusConnector(Protocol):
    """Fetches and searches raw documents (decisions and statutes) in one store.

    A connector holds no legal logic: it returns each document as a mapping and the core
    checks it against the decision record. One connector may serve several jurisdictions.
    A connector that can enumerate its store also has `list_ids()`; one that cannot raises
    `ListingNotSupported` from it or does not define it (decision 0025). A connector whose
    results describe their documents also has `search_results(text, limit, filters)`, which
    returns each result's citation, type and matched passage where the store gives them, and
    applies `filters` to the search (decision 0037).
    """

    def fetch(self, decision_id: str) -> dict[str, Any]:
        """One document as stored, keyed by the decision record's field names."""
        ...

    def search(self, text: str, limit: int) -> list[str]:
        """The ids of the documents that best match the text, best first."""
        ...


def list_ids(connector: Any) -> Iterable[str]:
    """Every id the store holds, or `ListingNotSupported`."""
    listing = getattr(connector, "list_ids", None)
    if listing is None:
        raise ListingNotSupported(f"{type(connector).__name__} cannot list its documents")
    return listing()


def search_results(
    connector: Any, text: str, limit: int, filters: dict[str, Any]
) -> list[SearchResult]:
    """The results with whatever the connector says about them; ids alone when it says nothing."""
    described = getattr(connector, "search_results", None)
    if described is not None:
        return described(text, limit, filters)
    if filters:
        raise FiltersNotSupported(f"{type(connector).__name__} cannot filter its searches")
    return [SearchResult(id=found) for found in connector.search(text, limit)]
