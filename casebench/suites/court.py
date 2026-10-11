"""Court-derived suites: answer keys turned into cases by type, filtered and balanced."""

from collections import defaultdict
from datetime import date
from typing import Any

from casebench.core.case import Case
from casebench.extract.prompt import OUTCOMES
from casebench.references.court import AnswerKey, case_from_answer_key
from casebench.suites.generate import rank

QUESTIONS = {
    "outcome": "How did the court rule? Answer with exactly one of: " + ", ".join(OUTCOMES) + ".",
    "statute": "Which statutes and articles decide this dispute?",
    "precedent": "Which earlier court decisions does this dispute turn on?",
}
FACT_KINDS = {"outcome": "outcome", "statute": "statute", "precedent": "precedent"}


class NotEnoughLevels(ValueError):
    """Stratifying by court needs the provider to say each decision's court level."""


def cases_for(key: AnswerKey, task: str) -> Case | None:
    """One case of a type from a key that holds that type's facts, with only those facts."""
    facts = [fact for fact in key.facts if fact.kind == FACT_KINDS[task]]
    if not facts:
        return None
    narrowed = key.model_copy(
        update={
            "facts": facts,
            "inputs": {**key.inputs, "question": QUESTIONS[task]},
        }
    )
    return case_from_answer_key(narrowed, task=task, metrics=[task])


def _balanced(suite_id: str, cases: list[tuple[Case, str]], n: int) -> list[Case]:
    by_level: dict[str, list[Case]] = defaultdict(list)
    for case, level in cases:
        by_level[level].append(case)
    levels = sorted(by_level)
    chosen: list[Case] = []
    for index, level in enumerate(levels):
        quota = n // len(levels) + (1 if index < n % len(levels) else 0)
        ranked = sorted(by_level[level], key=lambda c: rank(suite_id, c.id))
        chosen += ranked[:quota]
    return chosen


def court_suite(
    suite_id: str,
    keys: list[AnswerKey],
    types: list[str],
    n: int,
    *,
    after: date | None = None,
    stratify: bool = False,
) -> tuple[list[Case], dict[str, Any]]:
    """The cases, in the suite's order, and what the manifest records about how they were made."""
    allowed = [k for k in keys if after is None or (k.date is not None and k.date > after)]
    candidates = [
        (case, key.level)
        for key in allowed
        for task in types
        if (case := cases_for(key, task)) is not None
    ]
    if stratify:
        missing = sum(1 for _, level in candidates if not level)
        if missing:
            raise NotEnoughLevels(f"{missing} cases come from decisions with no court level")
        chosen = _balanced(suite_id, [(c, str(level)) for c, level in candidates], n)
    else:
        chosen = [c for c, _ in candidates]
        chosen = sorted(chosen, key=lambda c: rank(suite_id, c.id))[:n]
    ordered = sorted(chosen, key=lambda c: rank(suite_id, c.id))
    generation = {
        "types": types,
        "requested": n,
        "after": after.isoformat() if after else None,
        "decisions_allowed": len(allowed),
        "decisions_excluded_by_date": len(keys) - len(allowed),
        "stratified_by": "court level" if stratify else None,
    }
    return ordered, generation
