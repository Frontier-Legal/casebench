"""Compare two runs of one suite, case by case, and mark what is noise (decision 0028)."""

from collections import defaultdict
from dataclasses import dataclass

from casebench.core.score import Score
from casebench.report.statistics import Interval, difference_interval, mean


@dataclass(frozen=True)
class Difference:
    task_type: str
    metric: str
    n: int
    first: float
    second: float
    interval: Interval

    @property
    def significant(self) -> bool:
        return not self.interval.contains(0.0)


def compare(first: list[Score], second: list[Score], suite_id: str) -> list[Difference]:
    """Only cases both runs scored with the same metric are paired."""
    before = {(s.case_id, s.metric): s for s in first}
    pairs: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for score in second:
        earlier = before.get((score.case_id, score.metric))
        if earlier is not None:
            pairs[(score.task_type, score.metric)].append((earlier.value, score.value))
    differences = []
    for (task_type, metric), values in sorted(pairs.items()):
        a, b = [v for v, _ in values], [v for _, v in values]
        differences.append(
            Difference(
                task_type,
                metric,
                len(values),
                mean(a),
                mean(b),
                difference_interval(a, b, suite_id),
            )
        )
    return differences
