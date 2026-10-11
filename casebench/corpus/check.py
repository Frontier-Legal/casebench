"""Sample a corpus and report which required fields its documents carry."""

import hashlib
from dataclasses import dataclass, field

from casebench.corpus.binding import Corpus
from casebench.corpus.interface import ListingNotSupported
from casebench.corpus.record import REQUIRED_FIELDS

# The corpus-check scenario samples 200 documents (decision 0025).
SAMPLE_SIZE = 200


@dataclass
class CheckReport:
    sampled: int = 0
    fetched: int = 0
    present: dict[str, int] = field(default_factory=lambda: dict.fromkeys(REQUIRED_FIELDS, 0))
    failures: list[str] = field(default_factory=list)

    @property
    def missing(self) -> list[str]:
        return [name for name, count in self.present.items() if count < self.sampled]


def _rank(decision_id: str) -> str:
    return hashlib.sha256(decision_id.encode()).hexdigest()


def sample_ids(corpus: Corpus, queries: list[str], size: int = SAMPLE_SIZE) -> list[str]:
    """A stable sample: by listing when the store can, otherwise through the given searches."""
    try:
        return sorted(corpus.decision_ids(), key=_rank)[:size]
    except ListingNotSupported:
        if not queries:
            raise
    found: list[str] = []
    for query in queries:
        for decision_id in corpus.search(query, size):
            if decision_id not in found:
                found.append(decision_id)
    return found[:size]


def check(corpus: Corpus, queries: list[str], size: int = SAMPLE_SIZE) -> CheckReport:
    report = CheckReport()
    before = corpus.connector.fetched
    for decision_id in sample_ids(corpus, queries, size):
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
