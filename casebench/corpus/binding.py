"""A corpus is a connector to a decision store, optionally filtered to one jurisdiction."""

from typing import Any

from pydantic import Field

from casebench.core.model import Record
from casebench.corpus.interface import CorpusConnector
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
    """Decisions read through any connector (decision 0024: no jurisdiction adapters)."""

    def __init__(self, config: CorpusConfig) -> None:
        connector_class = registry.load(
            kind_named("connector"), config.connector, config.connector_source
        )
        self.connector: CorpusConnector = connector_class(**config.options)
        self.jurisdiction = config.jurisdiction

    def decision(self, decision_id: str) -> DecisionRecord:
        return DecisionRecord.model_validate(self.connector.fetch(decision_id))

    def decision_ids(self) -> list[str]:
        """Every id in the store, or only the configured jurisdiction's."""
        ids = list(self.connector.list_ids())
        if self.jurisdiction is None:
            return ids
        return [i for i in ids if self.decision(i).jurisdiction == self.jurisdiction]
