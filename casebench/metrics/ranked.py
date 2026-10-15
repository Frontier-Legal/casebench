"""A research answer's authorities in rank order, against the gold authorities (decision 0049)."""

import math
from typing import ClassVar

from casebench.core.case import Case, Fact
from casebench.core.score import Direction, ScoreKind
from casebench.metrics.authorities import AuthorityMetric
from casebench.metrics.base import Verdict
from casebench.runs.log import Result
from casebench.suites.resolve import RESOLVED_KINDS

# How many of the answer's first authorities count.
TOP = 10
MISSED = "missed key authority"


def recall_at(ranked: list[str | None], gold: set[str], k: int = TOP) -> float:
    return len(gold & {d for d in ranked[:k] if d}) / len(gold)


def ndcg_at(ranked: list[str | None], gold: set[str], k: int = TOP) -> float:
    """Each gold authority has the same gain; one named twice counts at its first rank."""
    seen: set[str] = set()
    gains = []
    for document in ranked[:k]:
        gains.append(1.0 if document in gold and document not in seen else 0.0)
        if document:
            seen.add(document)
    found = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(len(gold), k)))
    return found / ideal


class RankedAuthorities(AuthorityMetric):
    """Resolves the answer's authorities as the statute and precedent metrics do, and keeps
    their order: the target's `citations` when it returned any, else the citations the judge
    lists from the answer, in the order they appear."""

    listed_kind = ""
    kind = ScoreKind.LLM
    direction = Direction.HIGHER
    version = "1"
    name: ClassVar[str]

    @staticmethod
    def gold(case: Case) -> list[Fact]:
        return [f for f in case.reference.facts if f.kind in RESOLVED_KINDS]

    @classmethod
    def evidenced(cls, case: Case) -> bool:
        """A case has nothing to find until it has gold authorities, each resolved to a corpus
        document; `casebench case resolve` resolves them."""
        gold = cls.gold(case)
        return bool(gold) and all(f.document_id for f in gold)

    def value(self, ranked: list[str | None], gold: set[str]) -> float:
        raise NotImplementedError

    def judge(self, case: Case, result: Result) -> Verdict:
        facts = self.gold(case)
        if any(f.document_id is None for f in facts):
            return Verdict(value=0.0, label="reference not resolved")
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        place = case.provenance.jurisdiction if case.provenance else None
        first = self.resolvers[0]
        items = [{"citation": c} for c in result.citations] or first.list_citations(result.output)
        matched = [resolver.resolve_all(items, place) for resolver in self.resolvers]
        decided = [
            self.decide(item, [resolved[position] for resolved in matched])
            for position, item in enumerate(items)
        ]
        ranked = [resolution.document_id for resolution, _ in decided]
        gold = {f.document_id for f in facts if f.document_id}
        top = set(ranked[:TOP])
        missed = [f.value for f in facts if f.document_id not in top]
        return Verdict(
            value=self.value(ranked, gold),
            label=f"{MISSED}: {'; '.join(missed)}" if missed else "all key authorities found",
            explanation=(
                f"recall@{TOP} {recall_at(ranked, gold):.2f}, nDCG@{TOP} "
                f"{ndcg_at(ranked, gold):.2f}; ranked {ranked[:TOP]}; gold {sorted(gold)}"
            ),
            judged_twice=len(items) if len(self.resolvers) > 1 else 0,
            disagreements=[differ for _, differ in decided if differ is not None],
        )
