"""How high a research answer ranks its gold authorities, as nDCG over the first ten (0049)."""

from casebench.metrics.ranked import RankedAuthorities, ndcg_at


class Metric(RankedAuthorities):
    name = "authority_ndcg"

    def value(self, ranked: list[str | None], gold: set[str]) -> float:
        return ndcg_at(ranked, gold)
