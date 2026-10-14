"""Count how often two judges agreed on the items they both decided, per metric (decision 0035)."""

from collections import defaultdict

from casebench.core.model import FrozenRecord
from casebench.core.score import Score


class JudgeAgreement(FrozenRecord):
    metric: str
    items: int
    disagreed: int
    rate: float


def agreement(scores: list[Score]) -> list[JudgeAgreement]:
    """Empty with one judge, since nothing was decided twice."""
    items: dict[str, int] = defaultdict(int)
    disagreed: dict[str, int] = defaultdict(int)
    for score in scores:
        items[score.metric] += score.judged_twice
        disagreed[score.metric] += len(score.disagreements)
    return [
        JudgeAgreement(
            metric=metric,
            items=n,
            disagreed=disagreed[metric],
            rate=(n - disagreed[metric]) / n,
        )
        for metric, n in sorted(items.items())
        if n
    ]
