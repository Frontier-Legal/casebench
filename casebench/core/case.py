"""The evaluation case: a task, a reference to grade against, and the metrics to apply."""

from enum import StrEnum
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, model_validator

from casebench.core.jurisdiction import Jurisdiction
from casebench.core.model import Record
from casebench.formats.extensions import Extensions
from casebench.formats.version import FormatVersion

FORMAT = FormatVersion("case", 1, 0)


class ReferenceSource(StrEnum):
    """Where a reference's facts came from."""

    COURT = "court"
    LAWYER = "lawyer"
    STRUCTURED = "structured"
    HYBRID = "hybrid"


class Approval(StrEnum):
    """Whether a lawyer has approved a case's reference."""

    DRAFT = "draft"
    APPROVED = "approved"


class Evidence(Record):
    """Where a fact can be checked: a span or anchor in a document, a quote, or a note."""

    doc: str
    span: tuple[int, int] | None = None
    anchor: str | None = None
    quote: str | None = None
    note: str | None = None


class Fact(Record):
    """One thing the reference asserts, tied to the evidence for it."""

    id: str
    kind: str
    value: str
    evidence: Evidence
    document_id: str | None = Field(
        default=None, description="The corpus document a cited authority resolved to."
    )


class Criterion(Record):
    """A pass/fail check on the output, derived from the reference's facts.

    A positive weight rewards meeting the criterion; a negative weight penalises
    triggering it. A negative criterion may stand without facts, because it names
    something the output must not do.
    """

    id: str
    text: str
    weight: int
    derived_from: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("from", "derived_from"),
        serialization_alias="from",
    )
    kind: str | None = None

    model_config = ConfigDict(extra="forbid", serialize_by_alias=True)

    @model_validator(mode="after")
    def _has_weight_and_source(self) -> "Criterion":
        if self.weight == 0:
            raise ValueError(f"criterion {self.id} has weight 0; it would never count")
        if self.weight > 0 and not self.derived_from:
            raise ValueError(f"criterion {self.id} rewards something no fact supports")
        return self


class Reference(Record):
    """What the output is graded against: evidenced facts and the criteria derived from them."""

    source: ReferenceSource
    facts: list[Fact] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
    author: str | None = None

    @model_validator(mode="after")
    def _criteria_cite_known_facts(self) -> "Reference":
        known = {fact.id for fact in self.facts}
        if len(known) != len(self.facts):
            raise ValueError("two facts share an id")
        for criterion in self.criteria:
            missing = set(criterion.derived_from) - known
            if missing:
                raise ValueError(f"criterion {criterion.id} cites unknown facts {sorted(missing)}")
        return self


class Task(Record):
    """What the AI is asked to do. Inputs beyond `type` are passed to the target by name."""

    type: str

    model_config = ConfigDict(extra="allow")

    @property
    def inputs(self) -> dict[str, Any]:
        return dict(self.model_extra or {})


class Provenance(Record):
    """How a case was made."""

    builder: str
    source_decision_id: str | None = None
    jurisdiction: Jurisdiction | None = None


class Case(Record):
    """One evaluation case."""

    id: str
    task: Task
    reference: Reference
    metrics: list[str]
    tags: list[str] = Field(default_factory=list)
    provenance: Provenance | None = None
    approval: Approval = Approval.DRAFT
    extensions: Extensions = Field(default_factory=dict)
