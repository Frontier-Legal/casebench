"""Three lines connect a Python agent in its own process (decision 0062).

    import casebench as cb
    cb.instrument()
    cb.run(my_agent, suite="suites/labour")

`instrument` patches the HTTP libraries the common model SDKs send through, so a run can
follow their calls; it creates no tracer and sets no variable. `run` asks each case of a
frozen suite, records the calls each answer made, stores and scores the run as `casebench run`
does, and returns the run's folder.
"""

import asyncio
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from casebench import network
from casebench.capture import redirect
from casebench.capture.functions import install
from casebench.capture.session import session_for
from casebench.config import DEFAULT_CONFIG, CasebenchConfig, load_config
from casebench.loading import accepted, call
from casebench.perimeter import enforce
from casebench.runs.cli import DEFAULT_RUNS, endpoint_target, show_scored
from casebench.runs.log import RunInfo, RunLog
from casebench.runs.runner import run_cases
from casebench.runs.scoring import prepare, score
from casebench.suites.freeze import load
from casebench.suites.qualify import as_qualified
from casebench.targets.answer import Answer, to_answer
from casebench.targets.load import target_from_config

IN_PROCESS = "python-in-process"


def instrument() -> list[str]:
    """Patch httpx2, httpx and requests, those installed, once; calls are unchanged until a
    run follows them. The libraries whose calls a run will record."""
    return redirect.patch()


class FunctionTarget:
    """The agent's own function, called in this process with the inputs it names."""

    def __init__(self, function: Callable[..., Any]) -> None:
        self.function = function

    async def start(self, slots: int = 1) -> None:
        return None

    async def answer(self, inputs: Mapping[str, Any]) -> Answer:
        return to_answer(await call(self.function, accepted(self.function, inputs)))

    async def stop(self) -> None:
        return None


def _config(path: Path, allow: list[str]) -> CasebenchConfig:
    config = load_config(path) if path.is_file() else CasebenchConfig()
    if allow:
        allowed = [*(config.network.allow if config.network else []), *allow]
        config = config.model_copy(update={"network": network.NetworkConfig(allow=allowed)})
    return config


async def arun(
    agent: Callable[..., Any] | str,
    suite: str | Path,
    *,
    config: str | Path = DEFAULT_CONFIG,
    runs_dir: str | Path = DEFAULT_RUNS,
    run_id: str | None = None,
    allow: list[str] | None = None,
) -> Path:
    """`run`, inside an event loop that is already running, such as a notebook's."""
    settings = _config(Path(config), allow or [])
    if isinstance(agent, str):
        settings = settings.model_copy(update={"target": endpoint_target(agent)})
    enforce(settings)
    try:
        return await _run(agent, Path(suite), settings, Path(runs_dir), run_id)
    finally:
        network.release()


async def _run(
    agent: Callable[..., Any] | str,
    suite: Path,
    config: CasebenchConfig,
    runs_dir: Path,
    run_id: str | None,
) -> Path:
    manifest, cases = load(suite)
    cases = as_qualified(cases, list(config.corpora))
    prepare(cases, config)
    if isinstance(agent, str):
        target: Any = target_from_config(config.target or {})
        kind, capture = "http", None
    else:
        patched = instrument()
        target, kind = FunctionTarget(agent), IN_PROCESS
        capture = session_for(config.capture, config.corpora, in_process=True)
        if capture.functions:
            install(capture.functions)
        print(f"casebench: recording calls made through {', '.join(patched) or 'nothing'}")
    run_id = run_id or f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    folder = runs_dir / run_id
    log = (
        RunLog(folder)
        if folder.is_dir()
        else RunLog.create(
            folder,
            RunInfo(
                run_id=run_id,
                suite_id=manifest.suite_id,
                suite_hash=manifest.content_hash,
                target=kind,
            ),
        )
    )
    sent = await run_cases(cases, target, log, max_concurrency=1, capture=capture)
    print(f"run {run_id}: {len(sent)} cases sent, {len(log.results())} stored\n{log.folder}")
    scored = await asyncio.to_thread(score, log, cases, config, manifest.suite_id)
    show_scored(log, scored, manifest.suite_id, runs_dir)
    return log.folder


def run(
    agent: Callable[..., Any] | str,
    suite: str | Path,
    *,
    config: str | Path = DEFAULT_CONFIG,
    runs_dir: str | Path = DEFAULT_RUNS,
    run_id: str | None = None,
    allow: list[str] | None = None,
) -> Path:
    """Ask every case of the frozen suite in `suite`, one at a time, and score the run.

    `agent` is a function, sync or async, or a generator, called with the case's inputs it
    names; a URL sends each case to that HTTP endpoint instead. `casebench.yaml`, when there
    is one, gives the judges, the corpora and the perimeter; `allow` adds hosts the agent
    calls. A run named by `run_id` that exists already resumes. Returns the run's folder.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            arun(agent, suite, config=config, runs_dir=runs_dir, run_id=run_id, allow=allow)
        )
    raise RuntimeError("an event loop is running here; use `await casebench.arun(...)`")
