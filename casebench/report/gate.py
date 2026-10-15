"""The gate: a run against a saved baseline, failing only on a significant drop (0048)."""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean

from casebench.core.case import Approval
from casebench.core.score import CitationLabel, Direction, Score
from casebench.report.calibration import OTHER, lawyers_win, read_reviews
from casebench.report.comparable import Change, changes
from casebench.report.compare import Difference, compare
from casebench.runs.log import Result, RunLog

PASSED, DROPPED, CANNOT_JUDGE = 0, 1, 2
# What a gate comment starts with, so the action finds and updates its own comment.
MARKER = "<!-- casebench-gate -->"
NOT_ERRORS = {CitationLabel.VERIFIED, CitationLabel.UNCHECKED}


class CannotJudge(ValueError):
    """The two runs measure differently, so a difference would not be the agent's."""


@dataclass(frozen=True)
class Row:
    difference: Difference
    direction: Direction
    grew: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def dropped(self) -> bool:
        """Significantly worse, in the metric's own direction."""
        interval = self.difference.interval
        return interval.high < 0 if self.direction is Direction.HIGHER else interval.low > 0


@dataclass(frozen=True)
class Gated:
    rows: list[Row]
    kept: int
    drafts: int
    include_unreviewed: bool
    latency_ms: tuple[float | None, float | None]
    tokens: tuple[float | None, float | None]

    @property
    def code(self) -> int:
        return DROPPED if any(row.dropped for row in self.rows) else PASSED


def latest(folder: Path) -> Path:
    sets = RunLog(folder).score_sets()
    if not sets:
        raise CannotJudge(f"{folder} has no scores yet; score it first")
    return sets[-1]


def error_types(scores: list[Score]) -> Counter[str]:
    """What went wrong: each citation's label, the kind of each failed criterion, else the
    score's own label."""
    counted: Counter[str] = Counter()
    for score in scores:
        found = [f"{c.label.value} citations" for c in score.citations if c.label not in NOT_ERRORS]
        found += [f"failed {v.kind or OTHER} criteria" for v in score.criteria if not v.passed]
        if not found and score.value < 1 and score.label:
            found = [score.label]
        counted.update(found)
    return counted


def _means(results: list[Result], kept: set[str]) -> tuple[float | None, float | None]:
    """The mean latency and the mean tokens the agent's recorded model calls used."""
    chosen = [r for r in results if r.case_id in kept]
    latencies = [r.latency_ms for r in chosen if r.latency_ms is not None]
    tokens = [
        sum((s.input_tokens or 0) + (s.output_tokens or 0) for s in r.steps)
        for r in chosen
        if r.steps
    ]
    return (fmean(latencies) if latencies else None, fmean(tokens) if tokens else None)


def gate(baseline: Path, run: Path, include_unreviewed: bool = False) -> Gated:
    first, second = RunLog(baseline), RunLog(run)
    if first.info.suite_hash != second.info.suite_hash:
        raise CannotJudge("the two runs ran different suites; gate runs of one suite")
    sets = latest(baseline), latest(run)
    before, after = (RunLog.read_producer(path) for path in sets)
    if before is None or after is None:
        raise CannotJudge("a score set is from before score sets said what produced them")
    moving: list[Change] = [c for c in changes(before, after) if c.moves]
    if moving:
        named = "; ".join(f"{c.setting}: {c.first} -> {c.second}" for c in moving)
        raise CannotJudge(
            f"the two runs were measured differently ({named}); score the baseline again with "
            "the run's settings"
        )
    # The scores the report shows: a lawyer's verdict replaces the judge's (0047).
    old, new = (
        lawyers_win(RunLog.read_scores(path), read_reviews(log.folder))
        for path, log in zip(sets, (first, second), strict=True)
    )
    allowed = {Approval.APPROVED} | ({Approval.DRAFT} if include_unreviewed else set())
    drafts = {s.case_id for s in new if s.approval is Approval.DRAFT}
    old, new = ([s for s in scores if s.approval in allowed] for scores in (old, new))
    kept = {s.case_id for s in new}
    directions = {s.metric: s.direction for s in new}
    rows = []
    for difference in compare(old, new, first.info.suite_id):
        mine = [
            [
                s
                for s in scores
                if s.metric == difference.metric and s.task_type == difference.task_type
            ]
            for scores in (old, new)
        ]
        counts = [error_types(scores) for scores in mine]
        grew = {
            kind: (counts[0][kind], counts[1][kind])
            for kind in sorted(counts[1])
            if counts[1][kind] > counts[0][kind]
        }
        rows.append(Row(difference, directions[difference.metric], grew))
    old_means, new_means = _means(first.results(), kept), _means(second.results(), kept)
    return Gated(
        rows=rows,
        kept=len(kept),
        drafts=0 if include_unreviewed else len(drafts),
        include_unreviewed=include_unreviewed,
        latency_ms=(old_means[0], new_means[0]),
        tokens=(old_means[1], new_means[1]),
    )


def _change(row: Row) -> str:
    d = row.difference
    return f"{d.interval.low:+.0%} to {d.interval.high:+.0%}"


def _verdict(row: Row) -> str:
    if row.dropped:
        return "worse, significant"
    return "significant" if row.difference.significant else "not significant"


def _pair(values: tuple[float | None, float | None], unit: str) -> str | None:
    if None in values:
        return None
    a, b = values
    return f"{a:.0f} -> {b:.0f} {unit}"


def lines(gated: Gated) -> list[str]:
    out = []
    if gated.include_unreviewed:
        out.append("gating approved and unreviewed cases (--include-unreviewed)")
    if not gated.kept:
        out.append(
            "0 approved cases: nothing to gate yet; --include-unreviewed gates the cases no "
            "lawyer has approved"
        )
    for row in gated.rows:
        d = row.difference
        out.append(
            f"{d.task_type} · {d.metric}: {d.first:.0%} -> {d.second:.0%} over {d.n} cases, "
            f"difference {_change(row)}, {_verdict(row)}"
        )
        out += [f"  {kind}: {before} -> {after}" for kind, (before, after) in row.grew.items()]
    if gated.drafts:
        out.append(f"{gated.drafts} draft cases were left out; a lawyer has not approved them")
    for name, values, unit in (
        ("latency", gated.latency_ms, "ms per case"),
        ("agent tokens", gated.tokens, "per case"),
    ):
        shown = _pair(values, unit)
        if shown:
            out.append(f"{name}: {shown} (reported, never gated)")
    out.append("gate: failed" if gated.code == DROPPED else "gate: passed")
    return out


def markdown(gated: Gated) -> str:
    """The pull request comment: each metric before and after, with its interval."""
    out = [MARKER, "### Casebench gate", ""]
    if gated.include_unreviewed:
        out += ["Approved and unreviewed cases (`--include-unreviewed`).", ""]
    if not gated.kept:
        out += ["0 approved cases: nothing to gate yet.", ""]
    if gated.rows:
        out += [
            "| Task · metric | Before | After | Cases | Difference | Change |",
            "|---|---|---|---|---|---|",
        ]
        for row in gated.rows:
            d = row.difference
            out.append(
                f"| {d.task_type} · {d.metric} | {d.first:.0%} | {d.second:.0%} | {d.n} "
                f"| {_change(row)} | {_verdict(row)} |"
            )
        grown = [(row, kind, pair) for row in gated.rows for kind, pair in row.grew.items()]
        if grown:
            out += ["", "Error types that grew:", ""]
            out += [f"- {row.difference.metric}: {kind}, {a} -> {b}" for row, kind, (a, b) in grown]
    if gated.drafts:
        out += ["", f"{gated.drafts} draft cases were left out; a lawyer has not approved them."]
    reported = [
        f"{name}: {shown}"
        for name, values, unit in (
            ("latency", gated.latency_ms, "ms per case"),
            ("agent tokens", gated.tokens, "per case"),
        )
        if (shown := _pair(values, unit))
    ]
    if reported:
        out += ["", "Reported, never gated: " + "; ".join(reported) + "."]
    out += ["", "**Gate failed.**" if gated.code == DROPPED else "**Gate passed.**", ""]
    return "\n".join(out)
