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


class CitationLabel(StrEnum):
    """`unchecked`: no connected corpus covers the citation's jurisdiction or kind, so
    Casebench cannot say; it never counts against the answer (decision 0036)."""

    VERIFIED = "verified"
    MISGROUNDED = "misgrounded"
    FABRICATED = "fabricated"
    UNCHECKED = "unchecked"


class CitationCheck(FrozenRecord):
    """One citation in an answer: as written, the claim it carried, what the corpus found."""

    citation: str
    claim: str
    label: CitationLabel
    document_id: str | None = None
    quote: str | None = None
    reason: str | None = None
    routed: str | None = Field(
        default=None,
        description="What chose the corpora searched: citation, case or all (decision 0036).",
    )


class Disagreement(FrozenRecord):
    """One item two judges decided differently; the stricter verdict is the one that counted,
    until a lawyer decides it (decision 0035)."""

    item: str
    first: str
    second: str


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
    citations: list[CitationCheck] = Field(default_factory=list)
    judged_twice: int = Field(default=0, description="Items both judges decided (decision 0035).")
    disagreements: list[Disagreement] = Field(default_factory=list)
    task_type: str
    reference_source: ReferenceSource
    approval: Approval
    jurisdiction: str | None = Field(
        default=None, description="The case's jurisdiction, so scores split by it (0036)."
    )
