"""The share of an editing case's clauses outside its issues the edit left unchanged (0049)."""

from casebench.core.case import Case
from casebench.core.score import Direction, ScoreKind
from casebench.metrics.base import Verdict
from casebench.metrics.clauses import changed, clauses, diff, issues
from casebench.runs.log import Result


class Metric:
    name = "edit_preservation"
    version = "1"
    kind = ScoreKind.CODE
    direction = Direction.HIGHER

    def __init__(self, **_: object) -> None:
        return None

    @staticmethod
    def evidenced(case: Case) -> bool:
        return bool(issues(case))

    def judge(self, case: Case, result: Result) -> Verdict:
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        document = str(case.task.inputs.get("document", ""))
        listed = {number for number, _ in issues(case)}
        outside = [number for number in clauses(document) if number not in listed]
        touched = [number for number in changed(document, result.output) if number in outside]
        if not outside:
            return Verdict(value=1.0, label="no clause outside the issues")
        return Verdict(
            value=1 - len(touched) / len(outside),
            label=f"changed outside the edit: {', '.join(touched)}" if touched else "preserved",
            explanation="\n".join(diff(document, result.output, number) for number in touched)
            or None,
        )
