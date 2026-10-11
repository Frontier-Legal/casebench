"""The corpus connector contract: where documents come from, never how to read them."""

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable


class ListingNotSupported(NotImplementedError):
    """The store cannot enumerate its documents; sample it through searches instead."""


@runtime_checkable
class CorpusConnector(Protocol):
    """Fetches and searches raw documents (decisions and statutes) in one store.

    A connector holds no legal logic: it returns each document as a mapping and the core
    checks it against the decision record. One connector may serve several jurisdictions.
    A connector that can enumerate its store also has `list_ids()`; one that cannot raises
    `ListingNotSupported` from it or does not define it (decision 0025).
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
