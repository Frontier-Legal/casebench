"""Write a suite's questions for a closed tool, and score its answers when they come back."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import click

from casebench.config import CasebenchConfig, load_config
from casebench.judge.judges import SameFamily
from casebench.metrics.loading import MetricNeeds
from casebench.perimeter import enforce
from casebench.pricing.lookup import lookup
from casebench.pricing.priced import priced
from casebench.runs.cli import show_scored
from casebench.runs.log import RunInfo, RunLog
from casebench.runs.offline import TARGET, AnswersError, read_answers, write_questions
from casebench.runs.scoring import prepare, score
from casebench.suites.freeze import load
from casebench.suites.qualify import as_qualified


def export_questions(suite_dir: Path, path: Path) -> None:
    _, cases = load(suite_dir)
    written = write_questions(cases, path)
    click.echo(f"wrote {written} questions to {path}; fill the answer column, then:")
    click.echo(f"  casebench import {path} --suite {suite_dir}")


def import_answers(
    path: Path, suite_dir: Path, config_path: Path, runs_dir: Path, run_id: str | None
) -> None:
    """A run of the tool's answers, scored as `casebench run` scores one (decision 0061)."""
    config = load_config(config_path) if config_path.is_file() else CasebenchConfig()
    # Priced from the sellers' lists before the run is held to its hosts (decision 0069).
    config = priced(config, lookup())
    enforce(config)
    manifest, cases = load(suite_dir)
    cases = as_qualified(cases, list(config.corpora))
    try:
        results, unanswered = read_answers(path, cases)
        prepare(cases, config)
    except (AnswersError, MetricNeeds, SameFamily) as failure:
        raise click.ClickException(str(failure)) from None
    if not results:
        raise click.ClickException(f"{path.name} has no answer filled in")
    run_id = run_id or f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    log = RunLog.create(
        runs_dir / run_id,
        RunInfo(
            run_id=run_id,
            suite_id=manifest.suite_id,
            suite_hash=manifest.content_hash,
            target=TARGET,
        ),
    )
    for result in results:
        log.append(result)
    click.echo(
        f"run {run_id}: {len(results)} answers from {path.name}"
        + (f", {len(unanswered)} cases unanswered" if unanswered else "")
    )
    answered = {r.case_id for r in results}
    scored = score(log, [c for c in cases if c.id in answered], config, manifest.suite_id)
    show_scored(log, scored, manifest.suite_id, runs_dir)
