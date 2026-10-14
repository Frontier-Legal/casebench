"""The criteria metric: the judge decides whether an answer meets each of a case's criteria."""

from typing import Any

from casebench.core.case import Case, Criterion
from casebench.core.score import CriterionVerdict, ScoreKind
from casebench.judge import prompts
from casebench.judge.client import Judge, JudgeReplyUnreadable
from casebench.metrics.criteria import WeightedCriteria


class JudgeGrader:
    """One call per answer: every criterion is decided in the same reply."""

    kind = ScoreKind.LLM

    def __init__(self, judge: Judge) -> None:
        self.model = judge

    def grade(self, case: Case, output: str, criteria: list[Criterion]) -> list[CriterionVerdict]:
        used = {fact_id for c in criteria for fact_id in c.derived_from}
        facts = [
            {"id": f.id, "kind": f.kind, "value": f.value, "evidence": f.evidence.quote}
            for f in case.reference.facts
            if f.id in used
        ]
        listed = [{"id": c.id, "text": c.text, "weight": c.weight} for c in criteria]
        reply = self.model.ask(
            prompts.GRADE, prompts.grade(case.task.inputs, facts, output, listed)
        )
        decided: dict[str, Any] = {
            str(item.get("id")): item for item in reply if isinstance(item, dict)
        }
        missing = [c.id for c in criteria if c.id not in decided]
        if missing:
            raise JudgeReplyUnreadable(f"the judge decided no verdict for {', '.join(missing)}")
        return [
            CriterionVerdict(
                criterion_id=c.id,
                weight=c.weight,
                met=decided[c.id].get("met") is True,
                quote=decided[c.id].get("quote"),
            )
            for c in criteria
        ]


class Metric(WeightedCriteria):
    """With two judges, a criterion passes only when both pass it (decision 0035)."""

    def __init__(self, judge: Judge, second_judge: Judge | None = None, **_: object) -> None:
        second = JudgeGrader(second_judge) if second_judge is not None else None
        super().__init__(JudgeGrader(judge), second)
