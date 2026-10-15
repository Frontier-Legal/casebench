"""`casebench export --review` and the review half of `casebench import` (decision 0055)."""

from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, load_config
from casebench.report.calibration import LawyerVerdict
from casebench.report.review_sheet import (
    ReviewSheetError,
    import_reviews,
    read_given,
    write_review_sheet,
)
from casebench.runs.cli import DEFAULT_RUNS
from casebench.runs.log import RUN_FILE, RunLog
from casebench.workbench.items import answer_key
from casebench.workbench.sources import Workspace
from casebench.workbench.store import DEFAULT_DATABASE, Event, Store, url_for

IMPORTED = "imported"


@click.command(name="export")
@click.option(
    "--review",
    "run_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="The run whose answers lawyers review in the spreadsheet.",
)
@click.option("--out", "path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--all", "everything", is_flag=True, help="Also the criteria already reviewed.")
@click.option(
    "--suites",
    "suite_dirs",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    multiple=True,
    help="Where to look for the run's suite; the current folder by default.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
    help="Its corpora's link: settings link each court fact to its decision.",
)
def export_command(
    run_dir: Path,
    path: Path | None,
    everything: bool,
    suite_dirs: tuple[Path, ...],
    config_path: Path,
) -> None:
    """Write a run's criteria to a spreadsheet lawyers review with no server and no login."""
    log = RunLog(run_dir)
    path = path or Path(f"review-{log.info.run_id}.xlsx")
    if path.exists():
        raise click.ClickException(f"{path} exists; name another file with --out")
    suite = (
        Workspace(run_dir.parent, list(suite_dirs) or [Path(".")]).suites().get(log.info.suite_id)
    )
    if suite is None:
        click.echo(
            f"no suite {log.info.suite_id} found, so the sheet names no question, criterion text "
            "or evidence; say where the suite is with --suites",
            err=True,
        )
    config = load_config(config_path) if config_path.is_file() else None
    try:
        written = write_review_sheet(
            log, suite.cases if suite else [], path, config.corpora if config else {}, everything
        )
    except ReviewSheetError as failure:
        raise click.ClickException(str(failure)) from None
    click.echo(f"wrote {written} rows to review to {path}")
    click.echo(f"then: casebench import {path}")


def _log_events(database: str | None, run_id: str, path: Path, made: list[LawyerVerdict]) -> None:
    """Into the workbench's event log when it has one, as the workbench logs a verdict."""
    url = database or (url_for(DEFAULT_DATABASE) if DEFAULT_DATABASE.is_file() else None)
    if url is None:
        return
    events = [
        Event(
            by=v.by,
            action="verdict",
            item=answer_key(run_id, v.case_id, v.repeat),
            subject=v.criterion_id,
            before=v.judge,
            after=v.verdict,
            reason=v.note,
        )
        for v in made
    ]
    events.append(
        Event(
            by=", ".join(sorted({v.by for v in made})),
            action=IMPORTED,
            item=f"run:{run_id}",
            subject=path.name,
            after={"verdicts": len(made)},
        )
    )
    Store(url).log(events)


def import_review_sheet(
    path: Path, run_id: str, runs_dir: Path | None, by: str | None, database: str | None
) -> None:
    folder = (runs_dir or DEFAULT_RUNS) / run_id
    if not (folder / RUN_FILE).is_file():
        raise click.ClickException(
            f"{path.name} reviews run {run_id}, which is not in {folder.parent}; say where the "
            "runs are with --runs-dir"
        )
    log = RunLog(folder)
    try:
        made = import_reviews(log, path, read_given(path, by))
    except ReviewSheetError as failure:
        raise click.ClickException(f"{failure}; nothing was imported") from None
    if not made:
        raise click.ClickException(f"{path.name} has no filled row")
    _log_events(database, run_id, path, made)
    overruled = sum(1 for v in made if v.verdict != v.judge)
    reviewers = ", ".join(sorted({v.by for v in made}))
    click.echo(
        f"imported {len(made)} verdicts on run {run_id} by {reviewers}, {overruled} overruling "
        "the judge; they replace the judge's in the report and the gate"
    )
