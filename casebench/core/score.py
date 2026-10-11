"""The one record every metric, judge and human review emits."""

from enum import StrEnum

from pydantic import Field

from casebench.core.case import Approval, ReferenceSource
from casebench.core.model import FrozenRecord


class ScoreKind(StrEnum):
    """Who produced a score."""

    CODE = "code"
    LLM = "llm"
    HUMAN = "human"


class Direction(StrEnum):
    """Which way is better."""

    HIGHER = "higher"
    LOWER = "lower"


class CriterionVerdict(FrozenRecord):
    """Whether the output met one criterion, with the quote that shows it."""

    criterion_id: str
    weight: int
    met: bool
    quote: str | None = None

    @property
    def passed(self) -> bool:
        """A positive criterion passes when met; a negative one passes when not triggered."""
        return self.met if self.weight > 0 else not self.met


class Score(FrozenRecord):
    """One metric's verdict on one output, carrying where its answer key came from."""

    case_id: str
    repeat: int = 0
    metric: str
    metric_version: str
    kind: ScoreKind
    direction: Direction
    value: float
    label: str | None = None
    explanation: str | None = None
    criteria: list[CriterionVerdict] = Field(default_factory=list)
    task_type: str
    reference_source: ReferenceSource
    approval: Approval
