"""A suite's history: each metric and error rate run by run, with its interval (decision 0067).

Lawyers' verdicts count in place of the judge's, sources and approval states are never averaged
together, and a run whose settings moved a metric is marked on that metric (decisions 0035, 0047).
"""

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from casebench.core.case import Case
from casebench.core.score import Score
from casebench.report.calibration import lawyers_win, read_reviews
from casebench.report.comparable import changes
from casebench.report.errors import error_rates
from casebench.report.partner import METRIC_NAMES
from casebench.report.statistics import mean, mean_interval
from casebench.runs.log import RunLog
from casebench.runs.producer import Producer
from casebench.workbench.items import NotFound
from casebench.workbench.sources import Workspace

# A score set's file name starts with the moment it was written (RunLog.write_score_set).
STAMP = "%Y%m%dT%H%M%SZ"
SUITE_CHANGED = "the suite"


class SuiteHistory(BaseModel):
    suite_id: str
    runs: int = Field(description="Scored runs of the suite.")
    last: datetime | None = Field(description="When its latest run was scored.")


class HistoryRun(BaseModel):
    run_id: str
    scored_at: datetime | None
    target: str
    commit: str | None
    changed: list[str] = Field(description="Settings that differ from the run before, by name.")


class Point(BaseModel):
    run_id: str
    n: int
    mean: float
    low: float
    high: float


class Series(BaseModel):
    """One metric for one reference source, approval state and practice area; `practice_area`
    None is every area together."""

    task_type: str
    metric: str
    name: str
    direction: str
    reference_source: str
    approval: str
    practice_area: str | None
    points: list[Point]
    moved: list[str] = Field(description="Runs whose settings moved this metric.")


class RateSeries(BaseModel):
    error: str
    meaning: str
    points: list[Point]


class History(BaseModel):
    suite_id: str
    runs: list[HistoryRun]
    series: list[Series]
    rates: list[RateSeries]


Key = tuple[str, str, str, str, str | None]


class _Scored:
    """One run's points, kept until its score set or its reviews change."""

    def __init__(
        self,
        producer: Producer | None,
        points: dict[Key, Point],
        rates: list[Any],
        directions: dict[tuple[str, str], str],
    ) -> None:
        self.producer = producer
        self.points = points
        self.rates = rates
        self.directions = directions


def scored_at(score_set: Path) -> datetime | None:
    try:
        return datetime.strptime(score_set.name[: len("YYYYmmddTHHMMSSZ")], STAMP).replace(
            tzinfo=UTC
        )
    except ValueError:
        return None


def _with_areas(scores: list[Score], cases: list[Case]) -> list[Score]:
    """The suite names each case's practice area, also for scores made before scores did."""
    areas = {case.id: case.practice_area for case in cases}
    return [
        s.model_copy(update={"practice_area": areas[s.case_id]}) if s.case_id in areas else s
        for s in scores
    ]


def _points(scores: list[Score], suite_id: str, run_id: str) -> dict[Key, Point]:
    grouped: dict[Key, list[float]] = defaultdict(list)
    for s in scores:
        base = (s.task_type, s.metric, s.reference_source.value, s.approval.value)
        grouped[(*base, None)].append(s.value)
        if s.practice_area:
            grouped[(*base, s.practice_area)].append(s.value)
    points = {}
    for key, values in grouped.items():
        interval = mean_interval(values, suite_id)
        points[key] = Point(
            run_id=run_id, n=len(values), mean=mean(values), low=interval.low, high=interval.high
        )
    return points


class Histories:
    """Each run's points, computed once per score set and set of reviews: a bootstrap interval
    costs milliseconds, and a history holds one per metric, source, area and run."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.held: dict[tuple[str, str, int, int], _Scored] = {}

    def suites(self) -> list[SuiteHistory]:
        found: dict[str, list[datetime | None]] = defaultdict(list)
        for log in self.workspace.runs():
            sets = log.score_sets()
            if sets:
                found[log.info.suite_id].append(scored_at(sets[-1]))
        out = []
        for suite_id, moments in found.items():
            known = [m for m in moments if m is not None]
            out.append(
                SuiteHistory(suite_id=suite_id, runs=len(moments), last=max(known, default=None))
            )
        return sorted(out, key=lambda s: (s.last is None, -(s.last.timestamp() if s.last else 0)))

    def _scored(self, log: RunLog, score_set: Path, cases: list[Case]) -> _Scored:
        reviews = log.folder / "reviews.jsonl"
        seen = reviews.stat() if reviews.is_file() else None
        key = (
            str(log.folder.resolve()),
            score_set.name,
            seen.st_mtime_ns if seen else 0,
            seen.st_size if seen else 0,
        )
        if key not in self.held:
            info = log.info
            scores = _with_areas(
                lawyers_win(RunLog.read_scores(score_set), read_reviews(log.folder)), cases
            )
            self.held[key] = _Scored(
                RunLog.read_producer(score_set),
                _points(scores, info.suite_id, info.run_id),
                error_rates(scores, info.suite_id),
                {(s.task_type, s.metric): s.direction.value for s in scores},
            )
        return self.held[key]

    def history(self, suite_id: str) -> History:
        logs = [
            log
            for log in self.workspace.runs()
            if log.info.suite_id == suite_id and log.score_sets()
        ]
        if not logs:
            raise NotFound(f"no scored run of suite {suite_id}")
        suite = self.workspace.suites().get(suite_id)
        cases = suite.cases if suite else []
        dated = [(scored_at(log.score_sets()[-1]), log) for log in logs]
        dated.sort(key=lambda pair: (pair[0] is None, pair[0] or datetime.min.replace(tzinfo=UTC)))
        runs: list[HistoryRun] = []
        series: dict[Key, list[Point]] = defaultdict(list)
        moved: dict[tuple[str, str], list[str]] = defaultdict(list)
        rates: dict[str, tuple[str, list[Point]]] = {}
        before: tuple[Producer | None, str] | None = None
        # Whether each metric is better higher or lower, as the latest run scores it.
        directions: dict[tuple[str, str], str] = {}
        for when, log in dated:
            info = log.info
            scored = self._scored(log, log.score_sets()[-1], cases)
            changed: list[str] = []
            if before is not None:
                producer, suite_hash = before
                if suite_hash != info.suite_hash:
                    changed.append(SUITE_CHANGED)
                if producer is not None and scored.producer is not None:
                    for change in changes(producer, scored.producer):
                        changed.append(change.setting)
                        for metric in change.moves:
                            moved[("metric", metric)].append(info.run_id)
                if SUITE_CHANGED in changed:
                    moved[("all", "")].append(info.run_id)
            before = (scored.producer, info.suite_hash)
            directions |= scored.directions
            runs.append(
                HistoryRun(
                    run_id=info.run_id,
                    scored_at=when,
                    target=info.target,
                    commit=info.commit,
                    changed=changed,
                )
            )
            for key, point in scored.points.items():
                series[key].append(point)
            for rate in scored.rates:
                _, points = rates.setdefault(rate.error, (rate.meaning, []))
                points.append(
                    Point(
                        run_id=info.run_id, n=rate.n, mean=rate.rate, low=rate.low, high=rate.high
                    )
                )
        return History(
            suite_id=suite_id,
            runs=runs,
            series=[
                Series(
                    task_type=task,
                    metric=metric,
                    name=METRIC_NAMES.get(metric, metric),
                    direction=directions.get((task, metric), "higher"),
                    reference_source=source,
                    approval=approval,
                    practice_area=area,
                    points=points,
                    moved=sorted(set(moved[("metric", metric)] + moved[("all", "")])),
                )
                for (task, metric, source, approval, area), points in sorted(
                    series.items(), key=lambda item: _order(item[0])
                )
            ],
            rates=[
                RateSeries(error=error, meaning=meaning, points=points)
                for error, (meaning, points) in rates.items()
            ],
        )


def _order(key: Key) -> tuple[Any, ...]:
    task, metric, source, approval, area = key
    return (task, metric, source, approval, area is not None, area or "")
