"""`casebench report` and `casebench compare`: read finished runs and extractions back."""

import json
from pathlib import Path

import click

from casebench.extract.compare import compare_lines, is_extraction
from casebench.formats.read import ignored_note, read
from casebench.formats.version import FormatVersion, UnreadableFormat
from casebench.report.calibration import calibration, read_reviews
from casebench.report.comparable import changes
from casebench.report.compare import compare
from casebench.report.record import FORMAT, Report
from casebench.report.render import (
    REPORT_FILE,
    calibration_lines,
    corpus_lines,
    error_lines,
    lines,
    suite_line,
    unevidenced_lines,
    warning_lines,
)
from casebench.runs.log import RunLog

RUN = click.Path(exists=True, file_okay=False, path_type=Path)


def latest_set(folder: Path) -> Path:
    sets = RunLog(folder).score_sets()
    if not sets:
        raise click.ClickException(f"{folder} has no scores yet")
    return sets[-1]


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
    if report.suite_hash:
        click.echo(suite_line(report.suite_id, report.suite_hash))
    for line in lines(report.tables, report.scores, report.funnel.summary):
        click.echo(line)
    for line in corpus_lines(report.produced_by):
        click.echo(line)
    for line in error_lines(report.scoring_errors, run_dir.name):
        click.echo(line)
    for line in unevidenced_lines(report.unevidenced):
        click.echo(line)
    # Lawyers' verdicts given since the run was scored count too (decision 0047).
    for line in calibration_lines(calibration(report.scores, read_reviews(run_dir))):
        click.echo(line)
    for line in warning_lines(report.warnings):
        click.echo(line, err=True)


@click.command(name="compare")
@click.argument("first", type=RUN)
@click.argument("second", type=RUN)
def compare_command(first: Path, second: Path) -> None:
    """Each metric before and after, with the interval of the difference, and every setting
    the two score sets were produced with differently. Given two keys folders, their
    extractions side by side: settings, agreement, time and cost."""
    if is_extraction(first) and is_extraction(second):
        for line in compare_lines(first, second):
            click.echo(line)
        return
    info = RunLog(first).info
    if RunLog(second).info.suite_hash != info.suite_hash:
        raise click.ClickException("the two runs ran different suites; compare runs of one suite")
    sets = latest_set(first), latest_set(second)
    before, after = (RunLog.read_producer(path) for path in sets)
    if before is None or after is None:
        click.echo("a score set is from before score sets said what produced them; score it again")
    found = changes(before, after) if before and after else []
    if found:
        click.echo("the two score sets were produced differently:")
    for change in found:
        click.echo(f"  {change.setting}: {change.first} -> {change.second}")
    scores = [RunLog.read_scores(path) for path in sets]
    for d in compare(scores[0], scores[1], info.suite_id):
        verdict = "significant" if d.significant else "not significant"
        moved = [c.setting for c in found if d.metric in c.moves]
        caveat = f"; not comparable, because of {', '.join(moved)}" if moved else ""
        click.echo(
            f"{d.task_type} · {d.metric}: {d.first:.0%} -> {d.second:.0%} over {d.n} "
            f"cases, difference {d.interval.low:+.0%} to {d.interval.high:+.0%}, {verdict}"
            f"{caveat}"
        )
