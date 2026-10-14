"""Score a finished run again, from its stored results alone."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from casebench.core.case import Case
from casebench.core.score import Score
from casebench.metrics.base import Metric, score
from casebench.runs.log import Result, RunLog, ScoringError
from casebench.runs.producer import Producer


def _score_one(
    case: Case, result: Result, metrics: list[Metric]
) -> tuple[list[Score], list[ScoringError]]:
    """Every metric the case names; one that fails is recorded and the others still score."""
    scores, errors = [], []
    for metric in metrics:
        if metric.name not in case.metrics:
            continue
        try:
            scores.append(score(metric, case, result))
        except Exception as failure:
            errors.append(
                ScoringError(
                    case_id=case.id,
                    repeat=result.repeat,
                    metric=metric.name,
                    error=f"{type(failure).__name__}: {failure}",
                )
            )
    return scores, errors


def rescore(
    log: RunLog,
    cases: list[Case],
    metrics: list[Metric],
    producer: Producer,
    concurrency: int = 1,
) -> Path:
    """Write a new score set beside the existing ones.

    It reads `results.jsonl` and the suite's cases; there is no target here to call.
    `producer` says what the metrics were built with, and becomes the set's first line. Up to
    `concurrency` cases are scored at once, and the set keeps the results' order (decision
    0037).
    """
    by_id = {case.id: case for case in cases}
    results = log.results()
    missing = {result.case_id for result in results} - by_id.keys()
    if missing:
        raise ValueError(f"the run has results for cases not in the suite: {sorted(missing)}")
    with ThreadPoolExecutor(max_workers=max(concurrency, 1)) as pool:
        scored = list(pool.map(lambda r: _score_one(by_id[r.case_id], r, metrics), results))
    scores = [s for case_scores, _ in scored for s in case_scores]
    errors = [e for _, case_errors in scored for e in case_errors]
    return log.write_score_set(scores, producer, errors)
