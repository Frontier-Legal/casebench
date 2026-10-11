"""A corpus is a connector bound to a jurisdiction adapter in the config."""

from typing import Any

from pydantic import Field

from casebench.adapters.interface import Citation, JurisdictionAdapter
from casebench.core.model import Record
from casebench.corpus.interface import CorpusConnector
from casebench.corpus.record import DecisionRecord
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


class CorpusConfig(Record):
    """`corpus:` in casebench.yaml. `*_source` names the distribution when two clash."""

    connector: str
    jurisdiction: str
    options: dict[str, Any] = Field(default_factory=dict)
    connector_source: str | None = None
    adapter_source: str | None = None


class Corpus:
    """Decisions of one jurisdiction, read through any connector."""

    def __init__(self, config: CorpusConfig) -> None:
        connector_class = registry.load(
            kind_named("connector"), config.connector, config.connector_source
        )
        adapter_class = registry.load(
            kind_named("adapter"), config.jurisdiction, config.adapter_source
        )
        self.connector: CorpusConnector = connector_class(**config.options)
        self.adapter: JurisdictionAdapter = adapter_class()
        self.jurisdiction = config.jurisdiction

    def decision(self, decision_id: str) -> DecisionRecord:
        return DecisionRecord.model_validate(self.connector.fetch(decision_id))

    def decision_ids(self) -> list[str]:
        """The ids of this corpus's jurisdiction; a store may hold several."""
        return [
            decision_id
            for decision_id in self.connector.list_ids()
            if self.decision(decision_id).jurisdiction == self.jurisdiction
        ]

    def citations(self, decision_id: str) -> list[Citation]:
        return self.adapter.citations(self.decision(decision_id).text)
