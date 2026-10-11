"""The outcome metric: the answer's ruling label against the court's, with no model."""

import re

from casebench.core.case import Case
from casebench.core.score import Direction, ScoreKind
from casebench.extract.prompt import OUTCOMES
from casebench.metrics.base import Verdict
from casebench.runs.log import Result

WRONG = "wrong outcome"
UNREADABLE = "unreadable outcome"


def labels_in(answer: str) -> set[str]:
    """The shared labels an answer states; "partly reversed" is not also "reversed"."""
    found: list[tuple[int, int, str]] = []
    for label in OUTCOMES:
        pattern = r"\b" + r"[\s_-]+".join(map(re.escape, label.split("_"))) + r"\b"
        found += [(m.start(), m.end(), label) for m in re.finditer(pattern, answer.casefold())]
    return {
        label
        for start, end, label in found
        if not any(s <= start and end <= e and (s, e) != (start, end) for s, e, _ in found)
    }


class Metric:
    name = "outcome"
    version = "1"
    kind = ScoreKind.CODE
    direction = Direction.HIGHER

    def __init__(self, **_: object) -> None:
        return None

    def judge(self, case: Case, result: Result) -> Verdict:
        expected = next(f.value for f in case.reference.facts if f.kind == "outcome")
        stated = labels_in(result.output or "")
        if len(stated) != 1:
            return Verdict(value=0.0, label=UNREADABLE, explanation=f"found {sorted(stated)}")
        [answer] = stated
        if answer == expected:
            return Verdict(value=1.0, label="correct")
        return Verdict(value=0.0, label=WRONG, explanation=f"answered {answer}, court: {expected}")
