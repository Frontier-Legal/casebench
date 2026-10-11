"""The contract every metric meets: read a case and its result, return a verdict."""

from typing import Protocol

from pydantic import Field

from casebench.core.case import Case
from casebench.core.model import FrozenRecord
from casebench.core.score import CriterionVerdict, Direction, Score, ScoreKind
from casebench.runs.log import Result


class Verdict(FrozenRecord):
    """What a metric decides about one output."""

    value: float
    label: str | None = None
    explanation: str | None = None
    criteria: list[CriterionVerdict] = Field(default_factory=list)


class Metric(Protocol):
    """Scores one aspect of one output. It reads the case and the result and never
    calls the system under test."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def kind(self) -> ScoreKind: ...

    @property
    def direction(self) -> Direction: ...

    def judge(self, case: Case, result: Result) -> Verdict: ...


def score(metric: Metric, case: Case, result: Result) -> Score:
    """Run a metric and label its verdict with the case's task, source and approval."""
    verdict = metric.judge(case, result)
    return Score(
        case_id=case.id,
        repeat=result.repeat,
        metric=metric.name,
        metric_version=metric.version,
        kind=metric.kind,
        direction=metric.direction,
        value=verdict.value,
        label=verdict.label,
        explanation=verdict.explanation,
        criteria=verdict.criteria,
        task_type=case.task.type,
        reference_source=case.reference.source,
        approval=case.approval,
    )
