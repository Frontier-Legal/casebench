"""Compare the authorities an answer cites with the court's, as corpus documents (decision 0029)."""

from typing import ClassVar

from casebench.core.case import Case
from casebench.core.score import Direction, ScoreKind
from casebench.corpus.corpora import Corpora
from casebench.judge import prompts
from casebench.judge.client import Judge
from casebench.judge.resolve import Resolver
from casebench.metrics.base import Verdict
from casebench.runs.log import Result


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

    def __init__(self, judge: Judge, corpus: Corpora, candidates: int, **_: object) -> None:
        self.model = judge
        self.resolver = Resolver(judge, corpus, candidates)

    def judge(self, case: Case, result: Result) -> Verdict:
        documents = [f.document_id for f in case.reference.facts if f.kind == self.name]
        court = {document_id for document_id in documents if document_id is not None}
        if not documents or len(court) < len(set(documents)):
            return Verdict(value=0.0, label="reference not resolved")
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        listed = self.model.ask(prompts.LIST_CITATIONS, prompts.list_citations(result.output))
        wanted = [
            str(item["citation"])
            for item in listed
            if item.get("kind", self.listed_kind) == self.listed_kind
        ]
        resolved = [self.resolver.resolve(citation).document_id for citation in wanted]
        cited = {document_id for document_id in resolved if document_id is not None}
        unresolved = resolved.count(None)
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
        )
