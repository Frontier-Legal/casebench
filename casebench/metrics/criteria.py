"""Weighted criteria: each criterion passes or fails with quoted evidence."""

import re
import unicodedata
from typing import Protocol

from casebench.core.case import Case, Criterion, Fact
from casebench.core.score import CriterionVerdict, Direction, Disagreement, ScoreKind
from casebench.metrics.base import Verdict
from casebench.runs.log import Result

PASSED = {True: "passed", False: "failed"}
UNQUOTED = "the judge found it met but quoted nothing the answer says, so it does not count"


class CriteriaGrader(Protocol):
    """Decides, for each criterion, whether the output meets it and quotes where."""

    @property
    def kind(self) -> ScoreKind: ...

    def grade(self, case: Case, output: str, criteria: list[Criterion]) -> list[CriterionVerdict]:
        """One verdict per criterion, in the criteria's order."""
        ...


def label_of(verdicts: list[CriterionVerdict]) -> str:
    failed = [v.criterion_id for v in verdicts if not v.passed]
    return "all criteria passed" if not failed else f"failed: {', '.join(failed)}"


def weighted_score(verdicts: list[CriterionVerdict]) -> float:
    """The weighted sum of met criteria over the sum of positive weights, clipped to 0 to 1.

    The scheme PRBench and BigLaw Bench use; decision 0002 cites it.
    """
    possible = sum(verdict.weight for verdict in verdicts if verdict.weight > 0)
    if possible == 0:
        raise ValueError("no positive criterion, so nothing can be earned")
    earned = sum(verdict.weight for verdict in verdicts if verdict.met)
    return min(1.0, max(0.0, earned / possible))


def _plain(text: str) -> str:
    """NFC, with each run of whitespace as one space, so line breaks do not hide a quote."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def held(quote: str | None, output: str) -> bool:
    """Whether the output holds the quote, word for word."""
    return bool(quote and _plain(quote)) and _plain(quote or "") in _plain(output)


def checked(verdicts: list[CriterionVerdict], output: str) -> list[CriterionVerdict]:
    """A verdict of met stands only on a quote the output holds; otherwise it counts as not
    met, and its note says why (decision 0047)."""
    return [
        verdict
        if not verdict.met or held(verdict.quote, output)
        else verdict.model_copy(update={"met": False, "quote": None, "note": UNQUOTED})
        for verdict in verdicts
    ]


def evidence_of(fact: Fact) -> str:
    """The court's passage, or what a lawyer wrote when there is none."""
    note = f" ({fact.evidence.note})" if fact.evidence.note else ""
    return fact.evidence.quote or f"{fact.value}{note}"


def _kind(case: Case, criterion: Criterion) -> str | None:
    facts = {fact.id: fact for fact in case.reference.facts}
    sources = [facts[i].kind for i in criterion.derived_from if i in facts]
    return criterion.kind or (sources[0] if sources else None)


def _grounded(case: Case, verdicts: list[CriterionVerdict]) -> list[CriterionVerdict]:
    """Each verdict with its criterion's kind and the evidence it rests on."""
    criteria = {criterion.id: criterion for criterion in case.reference.criteria}
    facts = {fact.id: fact for fact in case.reference.facts}
    return [
        v.model_copy(
            update={
                "kind": _kind(case, criteria[v.criterion_id]),
                "evidence": [
                    evidence_of(facts[i])
                    for i in criteria[v.criterion_id].derived_from
                    if i in facts
                ],
            }
        )
        for v in verdicts
    ]


class WeightedCriteria:
    """The `criteria` metric."""

    name = "criteria"
    version = "1"
    direction = Direction.HIGHER

    def __init__(self, grader: CriteriaGrader, second: CriteriaGrader | None = None) -> None:
        self.graders = [grader] if second is None else [grader, second]

    @property
    def grader(self) -> CriteriaGrader:
        return self.graders[0]

    @property
    def kind(self) -> ScoreKind:
        return self.grader.kind

    @staticmethod
    def evidenced(case: Case) -> bool:
        """A case with no criterion to earn is not scored for criteria: it is unevidenced
        (decision 0047)."""
        return any(criterion.weight > 0 for criterion in case.reference.criteria)

    def judge(self, case: Case, result: Result) -> Verdict:
        criteria = case.reference.criteria
        if result.output is None:
            verdicts = [
                CriterionVerdict(criterion_id=c.id, weight=c.weight, met=False) for c in criteria
            ]
            return Verdict(value=0.0, label="no output", criteria=verdicts)
        graded = [grader.grade(case, result.output, criteria) for grader in self.graders]
        for verdicts in graded:
            if [v.criterion_id for v in verdicts] != [c.id for c in criteria]:
                raise ValueError(
                    f"the grader did not return one verdict per criterion for {case.id}"
                )
        graded = [_grounded(case, checked(verdicts, result.output)) for verdicts in graded]
        verdicts, disagreements = both(*graded) if len(graded) > 1 else (graded[0], [])
        label = label_of(verdicts)
        return Verdict(
            value=weighted_score(verdicts),
            label=label,
            criteria=verdicts,
            judged_twice=len(verdicts) if len(graded) > 1 else 0,
            disagreements=disagreements,
        )


def both(
    first: list[CriterionVerdict], second: list[CriterionVerdict]
) -> tuple[list[CriterionVerdict], list[Disagreement]]:
    """A criterion passes only when both judges pass it (decision 0035): where they differ,
    the failing verdict counts."""
    kept, disagreements = [], []
    for a, b in zip(first, second, strict=True):
        kept.append(b if a.passed and not b.passed else a)
        if a.passed != b.passed:
            first_said, second_said = (PASSED[v.passed] for v in (a, b))
            disagreements.append(
                Disagreement(
                    item=f"criterion {a.criterion_id}", first=first_said, second=second_said
                )
            )
    return kept, disagreements
