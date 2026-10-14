"""A corpus is a named, cached connector to one document store, with the jurisdictions it covers."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from casebench.core.jurisdiction import Jurisdiction, UnknownJurisdiction, code
from casebench.core.model import Record
from casebench.corpus.cache import DEFAULT_CACHE, CachedConnector, corpus_key
from casebench.corpus.ids import UnqualifiedId, qualify, split
from casebench.corpus.interface import list_ids
from casebench.corpus.record import DecisionRecord
from casebench.corpus.results import SearchResult
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named

Holding = Literal["decisions", "statutes"]
Charge = Literal["search", "fetch", "none"]
# The kinds of citation the judge names (decision 0029).
Cited = Literal["statute", "decision"]
# What a provider's terms may let Casebench keep on disk (decision 0041).
Kept = Literal["documents", "searches"]


class CorpusConfig(Record):
    """One corpus in casebench.yaml. `jurisdictions` are the ones it covers, every one when
    empty; `holds` the kinds of documents it has, both when empty. `connector_source` names
    the distribution when two register the same connector; `profile` records which profile
    the options came from, and is never read again. `metered` is what the provider charges
    for: a store that charges per search has each search kept, like each document.
    `search_filters` are what a search for each kind of citation adds, so a statute is
    searched only among statutes (decision 0037). `keep` is what the provider's terms let
    Casebench keep on disk; left out, documents are kept, and searches when metered (0041).
    `probe` is the search the corpus was added with, which `casebench check` runs (0044)."""

    connector: str
    jurisdictions: list[Jurisdiction] = Field(default_factory=list)
    holds: list[Holding] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    connector_source: str | None = None
    profile: str | None = None
    metered: Charge = "none"
    search_filters: dict[Cited, dict[str, Any]] = Field(default_factory=dict)
    keep: list[Kept] | None = None
    probe: str | None = None

    @property
    def keeps_documents(self) -> bool:
        return self.keep is None or "documents" in self.keep

    @property
    def keeps_searches(self) -> bool:
        return self.metered == "search" and (self.keep is None or "searches" in self.keep)


def _code_or_none(value: str) -> str | None:
    try:
        return code(value)
    except UnknownJurisdiction:
        return None


class Corpus:
    """Documents read through any connector, each fetched once and then read from disk. Ids
    leave it qualified with its name, and only the provider's own part reaches the provider."""

    def __init__(
        self, config: CorpusConfig, name: str = "corpus", cache_root: Path = DEFAULT_CACHE
    ) -> None:
        connector_class = registry.load(
            kind_named("connector"), config.connector, config.connector_source
        )
        folder = cache_root / corpus_key(config.connector, config.options)
        self.connector = CachedConnector(
            connector_class(**config.options),
            folder,
            keep_searches=config.keeps_searches,
            keep_documents=config.keeps_documents,
        )
        self.name = name
        self.jurisdictions = list(config.jurisdictions)
        self.search_filters = config.search_filters

    def own(self, qualified: str) -> str:
        """The provider's id for one of this corpus's qualified ids."""
        corpus, document_id = split(qualified)
        if corpus != self.name:
            raise UnqualifiedId(f"{qualified} belongs to corpus {corpus}, not {self.name}")
        return document_id

    def raw(self, qualified: str) -> dict[str, Any]:
        return self.connector.fetch(self.own(qualified))

    def jurisdiction_of(self, written: str) -> str:
        """A document's jurisdiction as a code: its own label when that is one, else the
        corpus's when it covers exactly one, else the label as the provider wrote it."""
        found = _code_or_none(written)
        if found is None and len(self.jurisdictions) == 1:
            return self.jurisdictions[0]
        return found or written

    def decision(self, qualified: str) -> DecisionRecord:
        record = DecisionRecord.model_validate(self.raw(qualified))
        update = {"id": qualified, "jurisdiction": self.jurisdiction_of(record.jurisdiction)}
        return record.model_copy(update=update)

    def search(self, text: str, limit: int) -> list[str]:
        return [qualify(self.name, found) for found in self.connector.search(text, limit)]

    def search_results(self, text: str, limit: int, kind: str | None = None) -> list[SearchResult]:
        """Searched with the filters for `kind`, the kind of citation the judge named."""
        filters = self.search_filters.get(kind, {}) if kind in ("statute", "decision") else {}
        found = self.connector.search_results(text, limit, filters)
        return [r.model_copy(update={"id": qualify(self.name, r.id)}) for r in found]

    def decision_ids(self) -> list[str]:
        """Every id in the store, or only those in the jurisdictions the corpus lists."""
        ids = [qualify(self.name, found) for found in list_ids(self.connector)]
        if not self.jurisdictions:
            return ids
        return [i for i in ids if self.decision(i).jurisdiction in self.jurisdictions]
