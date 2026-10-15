"""The share of an extraction case's expected fields the answer matched (0049)."""

import json

from casebench.core.case import Case
from casebench.core.score import Direction, ScoreKind
from casebench.metrics.base import Verdict
from casebench.metrics.values import EXPECTED, matched
from casebench.runs.log import Result


class Metric:
    name = "fields"
    version = "1"
    kind = ScoreKind.CODE
    direction = Direction.HIGHER

    def __init__(self, **_: object) -> None:
        return None

    @staticmethod
    def evidenced(case: Case) -> bool:
        return any(f.kind == EXPECTED for f in case.reference.facts)

    def judge(self, case: Case, result: Result) -> Verdict:
        expected = {f.id: f.value for f in case.reference.facts if f.kind == EXPECTED}
        try:
            given = json.loads(result.output or "")
        except json.JSONDecodeError:
            given = None
        if not isinstance(given, dict):
            return Verdict(value=0.0, label="no JSON object of fields")
        how = {name: matched(value, given.get(name)) for name, value in expected.items()}
        wrong = [name for name, way in how.items() if way is None]
        explained = [
            f"{name}: {way}"
            if way
            else f"{name}: expected {expected[name]!r}, got {given.get(name)!r}"
            for name, way in how.items()
        ]
        return Verdict(
            value=(len(expected) - len(wrong)) / len(expected),
            label=f"wrong fields: {', '.join(wrong)}" if wrong else "all fields matched",
            explanation="; ".join(explained),
        )
