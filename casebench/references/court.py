"""Cases whose reference comes from a court decision's answer key."""

from datetime import date as date_type
from typing import Any

from pydantic import Field

from casebench.core.case import Case, Fact, Provenance, Reference, ReferenceSource, Task
from casebench.core.model import Record


class AnswerKey(Record):
    """What a court decision says is correct, as extracted from it.

    `inputs` is what the target is given (for example the facts up to the operative
    part); `facts` are the answers, each pointing at its passage in the decision.
    """

    decision_id: str
    jurisdiction: str
    inputs: dict[str, Any]
    facts: list[Fact] = Field(min_length=1)
    date: date_type | None = None
    court: str | None = None
    level: str | None = None


def case_from_answer_key(key: AnswerKey, *, task: str, metrics: list[str]) -> Case:
    """A draft case: lawyers have not approved a court-derived reference yet."""
    return Case(
        id=f"{key.decision_id}:{task}",
        task=Task.model_validate({"type": task, **key.inputs}),
        reference=Reference(source=ReferenceSource.COURT, facts=key.facts),
        metrics=metrics,
        provenance=Provenance(
            builder="court",
            source_decision_id=key.decision_id,
            jurisdiction=key.jurisdiction,
        ),
    )
