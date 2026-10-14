"""Sample a corpus and report which fields its documents and its search results carry."""

import hashlib
from dataclasses import dataclass, field

from casebench.corpus.binding import Corpus
from casebench.corpus.interface import ListingNotSupported
from casebench.corpus.record import REQUIRED_FIELDS
from casebench.corpus.results import DESCRIBED, SearchResult

# The corpus-check scenario samples 200 documents (decision 0025).
SAMPLE_SIZE = 200


@dataclass
class CheckReport:
    """`described` counts, of the `results` the queries returned, how many carry each
    description the judge matches a citation by (decision 0037)."""

    sampled: int = 0
    fetched: int = 0
    present: dict[str, int] = field(default_factory=lambda: dict.fromkeys(REQUIRED_FIELDS, 0))
    failures: list[str] = field(default_factory=list)
    results: int = 0
    described: dict[str, int] = field(default_factory=lambda: dict.fromkeys(DESCRIBED, 0))

    @property
    def missing(self) -> list[str]:
        return [name for name, count in self.present.items() if count < self.sampled]

    @property
    def undescribed(self) -> list[str]:
        return [name for name, count in self.described.items() if count < self.results]


def _rank(decision_id: str) -> str:
    return hashlib.sha256(decision_id.encode()).hexdigest()


def sample_ids(
    corpus: Corpus,
    queries: list[str],
    size: int = SAMPLE_SIZE,
    found: list[SearchResult] | None = None,
) -> list[str]:
    """A stable sample: by listing when the store can, otherwise through the given searches,
    or the results they already returned."""
    try:
        return sorted(corpus.decision_ids(), key=_rank)[:size]
    except ListingNotSupported:
        if not queries:
            raise
    if found is None:
        found = [result for query in queries for result in corpus.search_results(query, size)]
    return list(dict.fromkeys(result.id for result in found))[:size]


def check(corpus: Corpus, queries: list[str], size: int = SAMPLE_SIZE) -> CheckReport:
    """Each query is searched once; its results are described and, when the store cannot
    list its documents, sampled."""
    report = CheckReport()
    found = [result for query in queries for result in corpus.search_results(query, size)]
    report.results = len(found)
    for name in DESCRIBED:
        report.described[name] = sum(getattr(result, name) is not None for result in found)
    before = corpus.connector.fetched
    for decision_id in sample_ids(corpus, queries, size, found):
        report.sampled += 1
        try:
            raw = corpus.raw(decision_id)
        except Exception as error:
            report.failures.append(f"{decision_id}: {type(error).__name__}: {error}")
            continue
        for name in REQUIRED_FIELDS:
            report.present[name] += raw.get(name) not in (None, "")
    report.fetched = corpus.connector.fetched - before
    return report
