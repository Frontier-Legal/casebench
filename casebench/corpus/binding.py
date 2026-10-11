"""A corpus is a cached connector to a document store, optionally filtered to one jurisdiction."""

from pathlib import Path
from typing import Any

from pydantic import Field

from casebench.core.model import Record
from casebench.corpus.cache import DEFAULT_CACHE, CachedConnector, corpus_key
from casebench.corpus.interface import list_ids
from casebench.corpus.record import DecisionRecord
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


class CorpusConfig(Record):
    """`corpus:` in casebench.yaml. `jurisdiction` filters a store that serves several;
    `connector_source` names the distribution when two register the same connector."""

    connector: str
    jurisdiction: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    connector_source: str | None = None


class Corpus:
    """Documents read through any connector, each fetched once and then read from disk."""

    def __init__(self, config: CorpusConfig, cache_root: Path = DEFAULT_CACHE) -> None:
        connector_class = registry.load(
            kind_named("connector"), config.connector, config.connector_source
        )
        folder = cache_root / corpus_key(config.connector, config.options)
        self.connector = CachedConnector(connector_class(**config.options), folder)
        self.jurisdiction = config.jurisdiction

    def raw(self, decision_id: str) -> dict[str, Any]:
        return self.connector.fetch(decision_id)

    def decision(self, decision_id: str) -> DecisionRecord:
        return DecisionRecord.model_validate(self.raw(decision_id))

    def search(self, text: str, limit: int) -> list[str]:
        return self.connector.search(text, limit)

    def decision_ids(self) -> list[str]:
        """Every id in the store, or only the configured jurisdiction's."""
        ids = list(list_ids(self.connector))
        if self.jurisdiction is None:
            return ids
        return [i for i in ids if self.decision(i).jurisdiction == self.jurisdiction]
