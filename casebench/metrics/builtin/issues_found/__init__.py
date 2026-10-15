"""The share of an editing case's issues whose clause the edit changed (0049)."""

from casebench.core.case import Case
from casebench.core.score import Direction, ScoreKind
from casebench.metrics.base import Verdict
from casebench.metrics.clauses import changed, issues
from casebench.runs.log import Result


class Metric:
    name = "issues_found"
    version = "1"
    kind = ScoreKind.CODE
    direction = Direction.HIGHER

    def __init__(self, **_: object) -> None:
        return None

    @staticmethod
    def evidenced(case: Case) -> bool:
        return bool(issues(case))

    def judge(self, case: Case, result: Result) -> Verdict:
        listed = issues(case)
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        edited = changed(str(case.task.inputs.get("document", "")), result.output)
        missed = [f"{number}: {issue}" for number, issue in listed if number not in edited]
        found = [number for number, _ in listed if number in edited]
        return Verdict(
            value=len(found) / len(listed),
            label=f"missed issues: {'; '.join(missed)}" if missed else "all issues found",
            explanation=f"found in clauses {', '.join(found) or 'none'}",
        )
