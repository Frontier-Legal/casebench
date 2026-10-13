"""Write a run's report to the terminal and to report.json."""

from pathlib import Path

from casebench.core.score import Score
from casebench.report.citations import citation_rates
from casebench.report.funnel import CaseFunnel, FunnelSummary, funnel_lines
from casebench.report.record import FORMAT, Funnel, Report
from casebench.report.tables import Table

REPORT_FILE = "report.json"


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def lines(
    tables: list[Table], scores: list[Score], funnel: FunnelSummary | None = None
) -> list[str]:
    out: list[str] = []
    for table in tables:
        out.append(f"{table.task_type} · {table.metric}")
        out.append(
            f"  {'source':<8} {'approval':<16} {'n':>5} {'score':>6} "
            f"{'95% interval':>14} {'majority':>9} {'text-only':>9}"
        )
        for row in table.rows:
            interval = f"{_percent(row.low)}-{_percent(row.high)}"
            out.append(
                f"  {row.reference_source.value:<8} {row.approval:<16} {row.n:>5} "
                f"{_percent(row.mean):>6} {interval:>14} "
                f"{_percent(row.majority_baseline):>9} {_percent(row.text_only_baseline):>9}"
            )
    rates = [r for r in citation_rates(scores) if r.count]
    if rates:
        out.append("citations")
        out += [f"  {r.label.value:<12} {r.count:>5} {_percent(r.rate):>6}" for r in rates]
    if funnel is not None:
        out += funnel_lines(funnel)
    return out


def write(
    folder: Path,
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
        tables=tables,
        citations=citation_rates(scores),
        funnel=Funnel(summary=summary, cases=funnels),
        scores=scores,
    )
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path
