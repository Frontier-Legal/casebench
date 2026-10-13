"""`casebench report` and `casebench compare`: read finished runs back."""

import json
from pathlib import Path

import click

from casebench.core.score import Score
from casebench.formats.read import ignored_note, read
from casebench.formats.version import FormatVersion, UnreadableFormat
from casebench.report.compare import compare
from casebench.report.record import FORMAT, Report
from casebench.report.render import REPORT_FILE, lines
from casebench.runs.log import RunLog

RUN = click.Path(exists=True, file_okay=False, path_type=Path)


def latest_scores(folder: Path) -> list[Score]:
    sets = RunLog(folder).score_sets()
    if not sets:
        raise click.ClickException(f"{folder} has no scores yet")
    return RunLog.read_scores(sets[-1])


@click.command(name="report")
@click.argument("run_dir", type=RUN)
def report_command(run_dir: Path) -> None:
    """Print a scored run's report again."""
    path = run_dir / REPORT_FILE
    if not path.is_file():
        raise click.ClickException(f"{run_dir} has no {REPORT_FILE}; score it first")
    saved = json.loads(path.read_text(encoding="utf-8"))
    if "format" not in saved:
        raise UnreadableFormat(f"{path} names no format; score the run again")
    declared = FormatVersion.parse(saved["format"])
    report, ignored = read(Report, saved, declared, FORMAT)
    if ignored:
        click.echo(ignored_note(str(path), declared, FORMAT, ignored), err=True)
    for line in lines(report.tables, report.scores, report.funnel.summary):
        click.echo(line)


@click.command(name="compare")
@click.argument("first", type=RUN)
@click.argument("second", type=RUN)
def compare_command(first: Path, second: Path) -> None:
    """Each metric before and after, with the interval of the difference."""
    info = RunLog(first).info
    if RunLog(second).info.suite_hash != info.suite_hash:
        raise click.ClickException("the two runs ran different suites; compare runs of one suite")
    for d in compare(latest_scores(first), latest_scores(second), info.suite_id):
        verdict = "significant" if d.significant else "not significant"
        click.echo(
            f"{d.task_type} · {d.metric}: {d.first:.0%} -> {d.second:.0%} over {d.n} "
            f"cases, difference {d.interval.low:+.0%} to {d.interval.high:+.0%}, {verdict}"
        )
