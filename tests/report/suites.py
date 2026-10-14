"""Frozen outcome suites for the report tests."""

from pathlib import Path

from casebench.core.case import (
    Case,
    Criterion,
    Evidence,
    Fact,
    Reference,
    ReferenceSource,
    Task,
)
from casebench.suites.freeze import freeze

QUESTION = "How did the court rule? Answer with exactly one of: upheld, reversed."


def outcome_case(number: int, ruling: str, facts: str, metrics: list[str] | None = None) -> Case:
    return Case(
        id=f"case-{number:03d}",
        task=Task.model_validate({"type": "outcome", "question": QUESTION, "facts": facts}),
        reference=Reference(
            source=ReferenceSource.COURT,
            facts=[
                Fact(
                    id="outcome",
                    kind="outcome",
                    value=ruling,
                    evidence=Evidence(doc=f"decision-{number}", quote=f"The court {ruling}."),
                )
            ],
        ),
        metrics=metrics or ["outcome"],
    )


def mixed(count: int) -> list[Case]:
    """Two of every three rulings reversed; the facts of a reversed case mention the appeal."""
    cases = []
    for number in range(count):
        if number % 3:
            cases.append(outcome_case(number, "reversed", "The appeal court found an error."))
        else:
            cases.append(outcome_case(number, "upheld", "The lower court weighed the evidence."))
    return cases


def frozen(cases: list[Case], folder: Path, suite_id: str = "outcomes") -> Path:
    freeze(suite_id, cases, folder, {})
    return folder


def criteria_case(number: int, criteria: dict[str, int]) -> Case:
    """A lawyer's case graded by criteria such as "Mentions upheld", each with its weight."""
    fact = Fact(id="f1", kind="outcome", value="upheld", evidence=Evidence(doc="note"))
    return Case(
        id=f"case-{number:03d}",
        task=Task.model_validate(
            {"type": "qa", "question": QUESTION, "facts": "The lower court weighed it."}
        ),
        reference=Reference(
            source=ReferenceSource.LAWYER,
            facts=[fact],
            criteria=[
                Criterion(id=f"c{n}", text=text, weight=weight, derived_from=["f1"])
                for n, (text, weight) in enumerate(criteria.items(), start=1)
            ],
        ),
        metrics=["criteria"],
    )
