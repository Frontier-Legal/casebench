"""`casebench run`: send a frozen suite to the target and store every result."""

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from casebench.capture.session import session_for
from casebench.config import DEFAULT_CONFIG, CasebenchConfig, load_config, target_of
from casebench.judge.judges import SameFamily
from casebench.metrics.loading import MetricNeeds
from casebench.perimeter import enforce
from casebench.report import render
from casebench.report.errors import error_rates
from casebench.runs import first
from casebench.runs.commit import current_commit
from casebench.runs.dry_run import estimate
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.progress import Progress
from casebench.runs.runner import run_cases
from casebench.runs.scoring import Scored, prepare, score
from casebench.suites.freeze import load
from casebench.suites.qualify import as_qualified
from casebench.targets.interface import TargetDidNotStart
from casebench.targets.load import target_from_config

DEFAULT_RUNS = Path(".casebench") / "runs"


def _config(path: Path, python: str | None) -> CasebenchConfig:
    if path.is_file():
        config = load_config(path)
    elif python is not None:
        config = CasebenchConfig(target={"type": "python", "entry": python})
    else:
        raise click.ClickException(f"{path} does not exist; pass --config or --python")
    if python is not None:
        config = config.model_copy(update={"target": {"type": "python", "entry": python}})
    enforce(config)
    return config


def _log(runs: Path, run_id: str | None, info: dict[str, Any]) -> RunLog:
    """A named run that exists already resumes; otherwise a new run starts."""
    if run_id is not None and (runs / run_id).is_dir():
        return RunLog(runs / run_id)
    run_id = run_id or f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    return RunLog.create(runs / run_id, RunInfo(run_id=run_id, **info))


def _summary(log: RunLog, sent: list[Result]) -> str:
    stored = log.results()
    failed = sum(1 for result in stored if result.error)
    steps = sum(len(result.steps) for result in stored)
    return (
        f"run {log.folder.name}: {len(sent)} cases sent, {len(stored)} stored, "
        f"{failed} failed, {steps} steps captured\n{log.folder}"
    )


@click.command()
@click.option(
    "--suite",
    "suite_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help=f"The frozen suite; without it, {first.FIRST}, built on the first run (decision 0061).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option(
    "--python",
    "python",
    metavar="AGENT.PY[:FUNCTION]",
    help="Run a Python agent in this process; FUNCTION defaults to answer.",
)
@click.option(
    "--max-concurrency",
    type=click.IntRange(min=1),
    help="Cases at once; overrides the target's setting.",
)
@click.option("--run-id", help="Name the run; an existing run of that name resumes.")
@click.option(
    "--runs-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_RUNS,
    show_default=True,
)
@click.option("--no-capture", is_flag=True, help="Do not start the recording proxy.")
@click.option("--dry-run", is_flag=True, help="Count what the run would send; send nothing.")
@click.option(
    "--commit",
    help="The commit the agent's code is at; else GITHUB_SHA, else the folder's checkout.",
)
@click.option(
    "--sample",
    type=click.IntRange(min=1),
    default=first.SAMPLE,
    show_default=True,
    help="With no suite yet: how many decisions the first run reads.",
)
@click.option(
    "--cases",
    "case_count",
    type=click.IntRange(min=1),
    default=first.CASES,
    show_default=True,
    help="With no suite yet: how many cases the first run makes.",
)
@click.option("--yes", is_flag=True, help="With no suite yet: build it without asking.")
@click.pass_context
def run(
    ctx: click.Context,
    suite_dir: Path | None,
    config_path: Path,
    python: str | None,
    max_concurrency: int | None,
    run_id: str | None,
    runs_dir: Path,
    no_capture: bool,
    dry_run: bool,
    commit: str | None,
    sample: int,
    case_count: int,
    yes: bool,
) -> None:
    """Send every case of a frozen suite to the target, store each result and score the run.
    With no --suite, the first run builds one from the corpus, and a later run resumes it."""
    config = _config(config_path, python)
    if suite_dir is None:
        suite_dir = first.FIRST
        if not first.is_built(suite_dir) and not dry_run:
            first.build(ctx, config, config_path, suite_dir, sample, case_count, yes)
        if not first.is_built(suite_dir):
            raise click.ClickException(f"no suite at {suite_dir}; run without --dry-run first")
        if run_id is None:
            stopped = load(suite_dir)[0]
            run_id = first.unfinished(
                runs_dir, stopped.suite_id, stopped.content_hash, stopped.case_count
            )
            if run_id is not None:
                click.echo(f"resuming run {run_id}, which stopped before every case was answered")
    manifest, cases = load(suite_dir)
    cases = as_qualified(cases, list(config.corpora))
    if dry_run:
        existing = runs_dir / run_id if run_id else None
        stored = (
            {r.case_id for r in RunLog(existing).results()}
            if existing and existing.is_dir()
            else set()
        )
        for line in estimate(cases, stored, config).lines():
            click.echo(line)
        return
    try:
        prepare(cases, config)
    except (MetricNeeds, SameFamily) as error:
        raise click.ClickException(str(error)) from error
    target_config = target_of(config)
    target = target_from_config(target_config)
    concurrency = max_concurrency or int(target_config.get("max_concurrency", 1))
    capture = None if no_capture else session_for(config.capture, config.corpora)
    log = _log(
        runs_dir,
        run_id,
        {
            "suite_id": manifest.suite_id,
            "suite_hash": manifest.content_hash,
            "target": str(target_config.get("type")),
            "commit": current_commit(commit),
        },
    )
    # A terminal shows the summary; a log file gets a line per case as it finishes (0038).
    progress = None
    if not sys.stdout.isatty():
        progress = Progress(len(cases), click.echo)
    try:
        sent = asyncio.run(
            run_cases(
                cases,
                target,
                log,
                max_concurrency=concurrency,
                capture=capture,
                on_answered=progress.answered_one if progress else None,
            )
        )
    except TargetDidNotStart as error:
        raise click.ClickException(str(error)) from error
    click.echo(_summary(log, sent))
    scored = score(
        log,
        cases,
        config,
        manifest.suite_id,
        concurrency,
        on_scored=progress.scored_one if progress else None,
    )
    show_scored(log, scored, manifest.suite_id, runs_dir)


def show_scored(log: RunLog, scored: Scored, suite_id: str, runs_dir: Path) -> None:
    """What `casebench run` prints once a run is scored, and where to open it."""
    click.echo(render.suite_line(log.info.suite_id, log.info.suite_hash))
    for line in render.lines(scored.tables, scored.scores, scored.funnel):
        click.echo(line)
    for line in render.corpus_lines(RunLog.read_producer(scored.score_set)):
        click.echo(line)
    for line in render.error_lines(scored.errors, log.folder.name):
        click.echo(line)
    for line in render.error_rate_lines(error_rates(scored.scores, suite_id)):
        click.echo(line)
    for line in render.spend_lines(scored.spend):
        click.echo(line)
    for line in render.unevidenced_lines(scored.unevidenced):
        click.echo(line)
    for line in render.warning_lines(scored.warnings):
        click.echo(line, err=True)
    click.echo(str(scored.report))
    click.echo(f"open it in the workbench: casebench ui --runs-dir {runs_dir}")
