"""Write a run's report to the terminal and to report.json."""

from collections import Counter
from pathlib import Path

from casebench.core.score import Score
from casebench.corpus.routing import Route
from casebench.report.agreement import agreement
from casebench.report.citations import citation_rates
from casebench.report.funnel import CaseFunnel, FunnelSummary, funnel_lines
from casebench.report.record import FORMAT, Funnel, Report
from casebench.report.tables import Table
from casebench.runs.producer import Producer

REPORT_FILE = "report.json"
ROUTED = {
    Route.CITATION: "its own jurisdiction",
    Route.CASE: "the case's jurisdiction",
    Route.ALL: "every corpus",
}


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def lines(
    tables: list[Table], scores: list[Score], funnel: FunnelSummary | None = None
) -> list[str]:
    out: list[str] = []
    for table in tables:
        out.append(f"{table.task_type} · {table.metric}")
        out.append(
            f"  {'source':<8} {'approval':<16} {'place':<6} {'n':>5} {'score':>6} "
            f"{'95% interval':>14} {'majority':>9} {'text-only':>9}"
        )
        for row in table.rows:
            interval = f"{_percent(row.low)}-{_percent(row.high)}"
            out.append(
                f"  {row.reference_source.value:<8} {row.approval:<16} "
                f"{row.jurisdiction or '-':<6} {row.n:>5} "
                f"{_percent(row.mean):>6} {interval:>14} "
                f"{_percent(row.majority_baseline):>9} {_percent(row.text_only_baseline):>9}"
            )
    rates = [r for r in citation_rates(scores) if r.count]
    if rates:
        out.append("citations")
        out += [f"  {r.label.value:<12} {r.count:>5} {_percent(r.rate):>6}" for r in rates]
        routes = Counter(c.routed for s in scores for c in s.citations if c.routed)
        if routes:
            out.append(
                "  searched by: "
                + ", ".join(f"{routes[r.value]} {ROUTED[r]}" for r in Route if routes[r.value])
            )
    out += _judges(scores)
    if funnel is not None:
        out += funnel_lines(funnel)
    return out


def _judges(scores: list[Score]) -> list[str]:
    """Only with two judges; every disagreement is listed, since a lawyer decides each one."""
    agreed = agreement(scores)
    if not agreed:
        return []
    out = ["judges"]
    out += [
        f"  {a.metric}: agreed on {a.items - a.disagreed} of {a.items} items ({_percent(a.rate)})"
        for a in agreed
    ]
    differ = [(s, d) for s in scores for d in s.disagreements]
    if differ:
        out.append("  disagreements, counted as failed until a lawyer decides them:")
        out += [
            f"    {s.case_id} · {s.metric} · {d.item}: first {d.first}, second {d.second}"
            for s, d in differ
        ]
    return out


def write(
    folder: Path,
    produced_by: Producer,
    tables: list[Table],
    scores: list[Score],
    score_set: Path,
    funnels: list[CaseFunnel],
    summary: FunnelSummary,
) -> Path:
    path = folder / REPORT_FILE
    report = Report(
        format=str(FORMAT),
        score_set=score_set.name,
        produced_by=produced_by,
        tables=tables,
        citations=citation_rates(scores),
        agreement=agreement(scores),
        funnel=Funnel(summary=summary, cases=funnels),
        scores=scores,
    )
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path
