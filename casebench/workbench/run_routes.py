"""The Run page's routes, which start, follow and stop a run from the workbench.

They list the suites to run and say what a run will send and cost first (decision 0063).
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from casebench.runs import first
from casebench.workbench import running
from casebench.workbench.jobs import Busy, Jobs, JobView
from casebench.workbench.settings import Settings
from casebench.workbench.sources import Workspace


class RunAsked(BaseModel):
    suite_id: str | None = Field(default=None, description="None builds the first suite.")
    sample: int = Field(default=first.SAMPLE, ge=1)
    cases: int = Field(default=first.CASES, ge=1)
    run_id: str | None = Field(
        default=None, description="A run to resume: only what it misses is answered and scored."
    )


def router(
    settings: Settings,
    workspace: Workspace,
    jobs: Jobs,
    folder: Path,
    engineer: Callable[..., str],
) -> APIRouter:
    """`folder` is where the workbench was started, which `casebench run` runs in."""
    routes = APIRouter()

    def planned(body: RunAsked) -> running.Plan:
        try:
            return running.plan(
                settings.config, workspace, body.suite_id, body.sample, body.cases, body.run_id
            )
        except running.Unknown as missing:
            raise HTTPException(404, str(missing)) from None

    @routes.get("/api/run/suites")
    def suites(name: str = Depends(engineer)) -> list[running.SuiteChoice]:
        return running.suites(settings.config, workspace)

    @routes.post("/api/run/plan")
    def plan(body: RunAsked, name: str = Depends(engineer)) -> running.Plan:
        """What the run will send and cost; nothing is sent."""
        return planned(body)

    @routes.post("/api/run/start")
    def start(body: RunAsked, name: str = Depends(engineer)) -> JobView:
        found = planned(body)
        if not found.can_start or settings.path is None:
            raise HTTPException(422, found.why_not or "there is no casebench.yaml to run with")
        if body.run_id is not None and workspace.run(body.run_id) is None:
            raise HTTPException(404, f"no run {body.run_id!r} is found")
        suite = workspace.suites().get(body.suite_id) if body.suite_id else None
        argv = running.command(
            settings.path.resolve(),
            workspace.runs_dir.resolve(),
            suite.folder.resolve() if suite else None,
            body.sample,
            body.cases,
            body.run_id,
        )
        title = f"suite {body.suite_id}" if body.suite_id else "the first suite"
        try:
            return jobs.start(title, argv, folder, body.suite_id).snapshot()
        except Busy as busy:
            raise HTTPException(409, str(busy)) from None

    @routes.get("/api/run/current")
    def current(name: str = Depends(engineer), since: int = 0) -> JobView | None:
        job = jobs.current()
        return job.snapshot(since) if job else None

    @routes.post("/api/run/{job_id}/stop")
    def stop(job_id: str, name: str = Depends(engineer)) -> JobView:
        job = jobs.find(job_id)
        if job is None:
            raise HTTPException(404, "no such run was started here")
        job.stop()
        return job.snapshot()

    return routes
