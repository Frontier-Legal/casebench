"""Weighted criteria: each criterion passes or fails with quoted evidence."""

from typing import Protocol

from casebench.core.case import Case, Criterion
from casebench.core.score import CriterionVerdict, Direction, ScoreKind
from casebench.metrics.base import Verdict
from casebench.runs.log import Result


class CriteriaGrader(Protocol):
    """Decides, for each criterion, whether the output meets it and quotes where."""

    @property
    def kind(self) -> ScoreKind: ...

    def grade(self, case: Case, output: str, criteria: list[Criterion]) -> list[CriterionVerdict]:
        """One verdict per criterion, in the criteria's order."""
        ...


def weighted_score(verdicts: list[CriterionVerdict]) -> float:
    """The weighted sum of met criteria over the sum of positive weights, clipped to 0 to 1.

    The scheme PRBench and BigLaw Bench use; decision 0002 cites it.
    """
    possible = sum(verdict.weight for verdict in verdicts if verdict.weight > 0)
    if possible == 0:
        raise ValueError("no positive criterion, so nothing can be earned")
    earned = sum(verdict.weight for verdict in verdicts if verdict.met)
    return min(1.0, max(0.0, earned / possible))


class WeightedCriteria:
    """The `criteria` metric."""

    name = "criteria"
    version = "1"
    direction = Direction.HIGHER

    def __init__(self, grader: CriteriaGrader) -> None:
        self.grader = grader

    @property
    def kind(self) -> ScoreKind:
        return self.grader.kind

    def judge(self, case: Case, result: Result) -> Verdict:
        criteria = case.reference.criteria
        if result.output is None:
            verdicts = [
                CriterionVerdict(criterion_id=c.id, weight=c.weight, met=False) for c in criteria
            ]
            return Verdict(value=0.0, label="no output", criteria=verdicts)
        verdicts = self.grader.grade(case, result.output, criteria)
        if [v.criterion_id for v in verdicts] != [c.id for c in criteria]:
            raise ValueError(f"the grader did not return one verdict per criterion for {case.id}")
        failed = [v.criterion_id for v in verdicts if not v.passed]
        label = "all criteria passed" if not failed else f"failed: {', '.join(failed)}"
        return Verdict(value=weighted_score(verdicts), label=label, criteria=verdicts)
