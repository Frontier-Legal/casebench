"""`casebench run`: send a frozen suite to the target and store every result."""

import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from casebench.capture.config import routes_for
from casebench.capture.session import CaptureSession
from casebench.config import DEFAULT_CONFIG, CasebenchConfig, load_config, target_of
from casebench.metrics.loading import MetricNeeds
from casebench.report import render
from casebench.runs.dry_run import estimate
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.runner import run_cases
from casebench.runs.scoring import prepare, score
from casebench.suites.freeze import load
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
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
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
def run(
    suite_dir: Path,
    config_path: Path,
    python: str | None,
    max_concurrency: int | None,
    run_id: str | None,
    runs_dir: Path,
    no_capture: bool,
    dry_run: bool,
) -> None:
    """Send every case of a frozen suite to the target, store each result and score the run."""
    config = _config(config_path, python)
    manifest, cases = load(suite_dir)
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
        metrics = prepare(cases, config)
    except MetricNeeds as error:
        raise click.ClickException(str(error)) from error
    target_config = target_of(config)
    target = target_from_config(target_config)
    concurrency = max_concurrency or int(target_config.get("max_concurrency", 1))
    capture = None
    if not no_capture:
        port = config.capture.port if config.capture else 0
        functions = config.capture.functions if config.capture else []
        traces = config.capture.traces if config.capture else False
        capture = CaptureSession(routes_for(config.capture), port, functions, traces)
    log = _log(
        runs_dir,
        run_id,
        {
            "suite_id": manifest.suite_id,
            "suite_hash": manifest.content_hash,
            "target": str(target_config.get("type")),
        },
    )
    try:
        sent = asyncio.run(
            run_cases(
                cases,
                target,
                log,
                max_concurrency=concurrency,
                capture=capture,
            )
        )
    except TargetDidNotStart as error:
        raise click.ClickException(str(error)) from error
    click.echo(_summary(log, sent))
    scored = score(log, cases, metrics, manifest.suite_id)
    for line in render.lines(scored.tables, scored.scores):
        click.echo(line)
    click.echo(str(scored.report))
