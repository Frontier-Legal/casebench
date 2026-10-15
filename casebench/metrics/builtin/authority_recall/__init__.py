"""The share of a research case's gold authorities among the answer's first ten (0049)."""

from casebench.metrics.ranked import RankedAuthorities, recall_at


class Metric(RankedAuthorities):
    name = "authority_recall"

    def value(self, ranked: list[str | None], gold: set[str]) -> float:
        return recall_at(ranked, gold)
