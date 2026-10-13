"""Score a finished run again, from its stored results alone."""

from pathlib import Path

from casebench.core.case import Case
from casebench.metrics.base import Metric, score
from casebench.runs.log import RunLog
from casebench.runs.producer import Producer


def rescore(log: RunLog, cases: list[Case], metrics: list[Metric], producer: Producer) -> Path:
    """Write a new score set beside the existing ones.

    It reads `results.jsonl` and the suite's cases; there is no target here to call.
    `producer` says what the metrics were built with, and becomes the set's first line.
    """
    by_id = {case.id: case for case in cases}
    missing = {result.case_id for result in log.results()} - by_id.keys()
    if missing:
        raise ValueError(f"the run has results for cases not in the suite: {sorted(missing)}")
    scores = [
        score(metric, by_id[result.case_id], result)
        for result in log.results()
        for metric in metrics
        if metric.name in by_id[result.case_id].metrics
    ]
    return log.write_score_set(scores, producer)
