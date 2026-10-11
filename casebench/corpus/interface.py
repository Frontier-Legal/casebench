"""The corpus connector contract: where decisions come from, never how to read them."""

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CorpusConnector(Protocol):
    """Lists and fetches raw decisions from one store.

    A connector holds no jurisdiction logic: it returns each decision as a mapping
    and the core checks it against the decision record. The same connector serves any
    jurisdiction; the config binds it to an adapter per corpus.
    """

    def list_ids(self) -> Iterable[str]:
        """Every decision id the store holds, in a stable order."""
        ...

    def fetch(self, decision_id: str) -> dict[str, Any]:
        """One decision as stored, keyed by the decision record's field names."""
        ...
