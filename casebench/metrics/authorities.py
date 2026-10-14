"""Compare the authorities an answer cites with the court's, as corpus documents (decision 0029)."""

from dataclasses import replace
from typing import Any, ClassVar

from casebench.core.case import Case
from casebench.core.score import Direction, Disagreement, ScoreKind
from casebench.corpus.corpora import Corpora
from casebench.judge.client import Judge
from casebench.judge.resolve import Resolution, Resolver
from casebench.metrics.base import Verdict
from casebench.runs.log import Result

NO_DOCUMENT = "no document"


def precision_recall(cited: set[str], unresolved: int, court: set[str]) -> tuple[float, float]:
    """An authority the corpus could not resolve is a wrong one."""
    right = len(cited & court)
    answered = len(cited) + unresolved
    return (right / answered if answered else 0.0, right / len(court) if court else 0.0)


def f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


class AuthorityMetric:
    """F1 of the answer's documents of one kind against the documents the court relied on."""

    name: ClassVar[str]
    listed_kind: ClassVar[str]
    version = "1"
    kind = ScoreKind.LLM
    direction = Direction.HIGHER

    def __init__(
        self,
        judge: Judge,
        corpus: Corpora,
        candidates: int,
        second_judge: Judge | None = None,
        **_: object,
    ) -> None:
        self.resolvers = [Resolver(judge, corpus, candidates)]
        if second_judge is not None:
            self.resolvers.append(Resolver(second_judge, corpus, second_judge.config.candidates))

    def resolve(
        self, item: dict[str, Any], place: str | None
    ) -> tuple[Resolution, Disagreement | None]:
        """With two judges, a citation is the document both name, and none when they differ."""
        each = [resolver.resolve_listed(item, place) for resolver in self.resolvers]
        named = [r.document_id for r in each]
        if len(set(named)) == 1:
            return each[0], None
        first, second = (name or NO_DOCUMENT for name in named)
        differ = Disagreement(item=str(item["citation"]), first=first, second=second)
        unresolved = replace(
            each[0], document_id=None, reason="the judges named different documents"
        )
        return unresolved, differ

    def judge(self, case: Case, result: Result) -> Verdict:
        documents = [f.document_id for f in case.reference.facts if f.kind == self.name]
        court = {document_id for document_id in documents if document_id is not None}
        if not documents or len(court) < len(set(documents)):
            return Verdict(value=0.0, label="reference not resolved")
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        place = case.provenance.jurisdiction if case.provenance else None
        wanted = [
            item
            for item in self.resolvers[0].list_citations(result.output)
            if item.get("kind", self.listed_kind) == self.listed_kind
        ]
        decided = [self.resolve(item, place) for item in wanted]
        resolved = [resolution for resolution, _ in decided]
        disagreements = [differ for _, differ in decided if differ is not None]
        twice = sum(1 for r in resolved if not r.unchecked) if len(self.resolvers) > 1 else 0
        cited = {r.document_id for r in resolved if r.document_id is not None}
        # An unchecked citation could not be looked for, so it is not counted as wrong.
        unresolved = sum(1 for r in resolved if r.document_id is None and not r.unchecked)
        precision, recall = precision_recall(cited, unresolved, court)
        failures = [
            f"{what} {self.name}"
            for what, rate in (("missed", recall), ("wrong", precision))
            if rate < 1
        ]
        return Verdict(
            value=f1(precision, recall),
            label=", ".join(failures) or "correct",
            explanation=(
                f"precision {precision:.2f}, recall {recall:.2f}; cited {sorted(cited)} and "
                f"{unresolved} the corpus could not resolve; court {sorted(court)}"
            ),
            judged_twice=twice,
            disagreements=disagreements,
        )
