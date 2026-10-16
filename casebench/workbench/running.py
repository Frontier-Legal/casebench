"""What a run started from the workbench will do, said before anything is sent.

The suites it can run, what it will send and cost, and the `casebench run` command that does
it (decision 0063).
"""

import sys
from pathlib import Path

from pydantic import BaseModel, Field

from casebench.config import CasebenchConfig
from casebench.judge.judges import SameFamily
from casebench.metrics.loading import MetricNeeds
from casebench.runs import first
from casebench.runs.dry_run import estimate
from casebench.runs.scoring import prepare
from casebench.suites.freeze import load
from casebench.suites.qualify import as_qualified
from casebench.workbench.sources import Workspace


class SuiteChoice(BaseModel):
    suite_id: str
    folder: str
    cases: int
    first: bool = Field(description="The suite the first run builds, not built yet.")


class Plan(BaseModel):
    lines: list[str] = Field(description="What the run will send, as `--dry-run` says it.")
    can_start: bool
    why_not: str | None = None


class Unknown(LookupError):
    """No suite by that id is found; the message says so."""


def suites(config: CasebenchConfig | None, workspace: Workspace) -> list[SuiteChoice]:
    """Each suite found, and the first suite when the config can build it and it is not there."""
    found = [
        SuiteChoice(
            suite_id=suite_id, folder=str(folder.folder), cases=len(folder.cases), first=False
        )
        for suite_id, folder in sorted(workspace.suites().items())
    ]
    buildable = config is not None and config.extract is not None and bool(config.corpora)
    if buildable and not first.is_built(first.FIRST):
        found.insert(
            0, SuiteChoice(suite_id=first.SUITE_ID, folder=str(first.FIRST), cases=0, first=True)
        )
    return found


def plan(
    config: CasebenchConfig | None,
    workspace: Workspace,
    suite_id: str | None,
    sample: int,
    cases: int,
    run_id: str | None = None,
) -> Plan:
    """`suite_id` None is the first suite, built first when it is not there yet; otherwise the
    suite is run as it is. A run being resumed sends only the cases it has no answer for."""
    if config is None:
        return Plan(
            lines=[], can_start=False, why_not="there is no casebench.yaml; run casebench init"
        )
    if config.target is None:
        return Plan(lines=[], can_start=False, why_not="casebench.yaml configures no target to run")
    if suite_id is None and not first.is_built(first.FIRST):
        try:
            return Plan(lines=first.plan(config, first.FIRST, sample, cases), can_start=True)
        except first.NoFirstSuite as missing:
            return Plan(lines=[], can_start=False, why_not=str(missing))
    if suite_id is None:
        suite_cases = load(first.FIRST)[1]
    else:
        found = workspace.suites().get(suite_id)
        if found is None:
            raise Unknown(f"no suite {suite_id!r} is found")
        suite_cases = found.cases
    resumed = workspace.run(run_id) if run_id else None
    stored = {result.case_id for result in resumed.results()} if resumed else set()
    qualified = as_qualified(suite_cases, list(config.corpora))
    lines = estimate(qualified, stored, config).lines()
    try:
        prepare(qualified, config)
    except (MetricNeeds, SameFamily) as error:
        return Plan(lines=lines, can_start=False, why_not=str(error))
    return Plan(lines=lines, can_start=True)


def command(
    config_path: Path,
    runs_dir: Path,
    suite_folder: Path | None,
    sample: int,
    cases: int,
    run_id: str | None = None,
) -> list[str]:
    """`casebench run`, as a terminal runs it; with no suite folder, the first run, agreed to
    on the page. A run id resumes that run: it answers and scores only what is missing."""
    argv = [sys.executable, "-m", "casebench", "run", "--config", str(config_path)]
    argv += ["--runs-dir", str(runs_dir)]
    if run_id is not None:
        argv += ["--run-id", run_id]
    if suite_folder is not None:
        return [*argv, "--suite", str(suite_folder)]
    return [*argv, "--yes", "--sample", str(sample), "--cases", str(cases)]
