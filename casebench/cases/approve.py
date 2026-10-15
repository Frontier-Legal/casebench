"""A lawyer approves, edits or rejects each fact of a court draft (decision 0050)."""

from dataclasses import dataclass
from typing import Literal

from casebench.cases.build import criterion_for
from casebench.core.case import Approval, Case, Criterion, Evidence, Fact

Decision = Literal["approve", "edit", "reject"]
# The kinds of fact Casebench writes a criterion for, so an edited one gets its new text.
WRITTEN = ("outcome", "answer", "statute", "precedent")


class CannotApprove(ValueError):
    """The decisions leave a fact undecided, or edit one without a value or a reason."""


@dataclass(frozen=True)
class FactDecision:
    fact_id: str
    decision: Decision
    value: str | None = None
    reason: str | None = None


def _written_by_casebench(criterion: Criterion, fact: Fact) -> bool:
    return (
        fact.kind in WRITTEN
        and criterion.derived_from == [fact.id]
        and criterion.text == criterion_for(fact).text
    )


def _edited(fact: Fact, decided: FactDecision, by: str) -> Fact:
    """The lawyer's value, with the lawyer's note as its evidence; a resolved citation is
    resolved again, since the document it named may no longer be the one meant."""
    value, reason = (decided.value or "").strip(), (decided.reason or "").strip()
    if not value:
        raise CannotApprove(f"the edit of {fact.id} has no value")
    if not reason:
        raise CannotApprove(f"the edit of {fact.id} needs a reason")
    evidence = Evidence(doc=fact.evidence.doc, note=f"edited by {by}: {reason}")
    return fact.model_copy(update={"value": value, "evidence": evidence, "document_id": None})


def approve_draft(case: Case, decisions: list[FactDecision], by: str) -> Case | None:
    """The case approved with `by` as its reference's author, or None when every fact was
    rejected. A rejected fact is dropped with every criterion that comes from it."""
    given = {d.fact_id: d for d in decisions}
    undecided = [f.id for f in case.reference.facts if f.id not in given]
    if undecided:
        raise CannotApprove(f"decide every fact first; undecided: {', '.join(undecided)}")
    facts: list[Fact] = []
    rejected: set[str] = set()
    rewritten: dict[str, Criterion] = {}
    for fact in case.reference.facts:
        decided = given[fact.id]
        if decided.decision == "reject":
            rejected.add(fact.id)
            continue
        if decided.decision == "edit":
            edited = _edited(fact, decided, by)
            for criterion in case.reference.criteria:
                if _written_by_casebench(criterion, fact):
                    rewritten[criterion.id] = criterion_for(edited).model_copy(
                        update={"id": criterion.id, "weight": criterion.weight}
                    )
            fact = edited
        facts.append(fact)
    if not facts:
        return None
    criteria = [
        rewritten.get(c.id, c)
        for c in case.reference.criteria
        if not rejected & set(c.derived_from)
    ]
    reference = case.reference.model_copy(
        update={"facts": facts, "criteria": criteria, "author": by}
    )
    return case.model_copy(update={"reference": reference, "approval": Approval.APPROVED})
