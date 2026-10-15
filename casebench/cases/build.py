"""Turn what a lawyer approved into a case: facts with their evidence, and a criterion each."""

from dataclasses import dataclass, field

from casebench.cases.draft import Draft
from casebench.core.case import (
    Approval,
    Case,
    Criterion,
    Evidence,
    Fact,
    Provenance,
    Reference,
    ReferenceSource,
    Task,
)
from casebench.corpus.routing import as_code
from casebench.extract.reading import Item

# Evidence for what the reviewer wrote rather than took from a decision.
REVIEWER = "reviewer"


@dataclass(frozen=True)
class Written:
    """The case as the lawyer left it: `outcome` for a case from a decision, `answer` for one
    written by hand."""

    question: str
    facts: str = ""
    outcome: str | None = None
    answer: str | None = None
    statutes: list[str] = field(default_factory=list)
    precedents: list[str] = field(default_factory=list)


def _evidence(value: str, drafted: list[Item], doc: str | None, author: str) -> Evidence:
    """A fact left as drafted keeps its passage; one the lawyer wrote is the lawyer's."""
    kept = next((item for item in drafted if item.value == value), None)
    if kept is not None and doc is not None:
        return Evidence(doc=doc, span=kept.span, quote=kept.quote)
    return Evidence(doc=doc or REVIEWER, note=f"written by {author}")


def criterion_for(fact: Fact) -> Criterion:
    """Written from the fact by Casebench, never by a model (decision 0002)."""
    text = {
        "outcome": f'Passes if the answer concludes that the court ruled "{fact.value}". '
        "Fails if it concludes otherwise or does not say.",
        "answer": f"Passes if the answer reaches this conclusion: {fact.value} "
        "Fails if it reaches another conclusion or none.",
        "statute": f"Passes if the answer relies on {fact.value}. Fails if it does not.",
        "precedent": f"Passes if the answer relies on the decision {fact.value}. "
        "Fails if it does not.",
    }[fact.kind]
    return Criterion(id=f"c-{fact.id}", text=text, weight=1, derived_from=[fact.id])


def lawyer_case(case_id: str, written: Written, author: str, drafted: Draft | None) -> Case:
    """An approved case: `court` when it came from a decision, `lawyer` when written by hand."""
    doc = drafted.decision.id if drafted else None
    reading = drafted.reading if drafted else None
    facts: list[Fact] = []
    if written.outcome:
        found = [reading.outcome] if reading and reading.outcome else []
        evidence = _evidence(written.outcome, found, doc, author)
        facts.append(Fact(id="outcome-1", kind="outcome", value=written.outcome, evidence=evidence))
    if written.answer:
        evidence = Evidence(doc=REVIEWER, note=f"written by {author}")
        facts.append(Fact(id="answer-1", kind="answer", value=written.answer, evidence=evidence))
    for kind, values, items in (
        ("statute", written.statutes, reading.statutes if reading else []),
        ("precedent", written.precedents, reading.precedents if reading else []),
    ):
        facts += [
            Fact(id=f"{kind}-{n}", kind=kind, value=v, evidence=_evidence(v, items, doc, author))
            for n, v in enumerate(values, start=1)
        ]
    inputs = {"question": written.question} | ({"facts": written.facts} if written.facts else {})
    return Case(
        id=case_id,
        task=Task.model_validate({"type": "qa", **inputs}),
        reference=Reference(
            source=ReferenceSource.COURT if drafted else ReferenceSource.LAWYER,
            facts=facts,
            criteria=[criterion_for(fact) for fact in facts],
            author=author,
        ),
        metrics=["criteria"],
        provenance=Provenance(
            builder="lawyer",
            source_decision_id=doc,
            # A provider's label that is no jurisdiction code is left out (decision 0036).
            jurisdiction=as_code(drafted.decision.jurisdiction) if drafted else None,
            extracted_by=[drafted.model] if drafted else [],
        ),
        approval=Approval.APPROVED,
    )
