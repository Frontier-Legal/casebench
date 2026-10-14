"""Send every case of a suite to the target and store each result as it finishes."""

import asyncio
import time
from collections.abc import Callable

from casebench.capture.assemble import assemble
from casebench.capture.context import capturing
from casebench.capture.otlp.mapping import to_step, without_duplicates
from casebench.capture.session import CaptureSession
from casebench.core.case import Case
from casebench.runs.log import Result, RunLog
from casebench.targets.interface import Target


async def ask(
    case: Case,
    target: Target,
    capture: CaptureSession | None = None,
) -> Result:
    """One case, with the steps captured while it ran. A failure is the case's, not the run's."""
    traceparent = capture.recorder.begin(case.id) if capture else None
    with capturing(case.id, traceparent) as captured:
        started = time.perf_counter()
        error: str | None = None
        try:
            answer = await target.answer(case.task.inputs)
        except Exception as failure:
            answer, error = None, f"{type(failure).__name__}: {failure}"
        latency_ms = (time.perf_counter() - started) * 1000
    steps = captured.steps
    if capture is not None:
        spans = capture.recorder.take_spans(case.id)
        exchanges = capture.recorder.end(case.id, captured.worker)
        proxied = [step for exchange in exchanges for step in capture.parse(exchange)]
        traced = [step for span in spans if (step := to_step(span)) is not None]
        in_process = captured.steps + without_duplicates(traced, proxied)
        steps = assemble(exchanges, capture.parse, in_process)
    if answer is None:
        return Result(case_id=case.id, error=error, steps=steps, latency_ms=latency_ms)
    return Result(
        case_id=case.id,
        output=answer.text,
        citations=answer.citations,
        documents=answer.documents,
        steps=steps,
        latency_ms=latency_ms,
    )


async def run_cases(
    cases: list[Case],
    target: Target,
    log: RunLog,
    *,
    max_concurrency: int = 1,
    capture: CaptureSession | None = None,
    on_answered: Callable[[Result], None] | None = None,
) -> list[Result]:
    """At most `max_concurrency` cases at once; cases the log already holds are skipped. With
    nothing left to send, the target is never started, so a stored run is scored again
    without calling the agent (decision 0037). `on_answered` hears of each stored result."""
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")
    stored = {result.case_id for result in log.results()}
    pending = [case for case in cases if case.id not in stored]
    if not pending:
        return []
    slots = asyncio.Semaphore(max_concurrency)

    async def one(case: Case) -> Result:
        async with slots:
            result = await ask(case, target, capture)
        log.append(result)
        if on_answered is not None:
            on_answered(result)
        return result

    if capture is not None:
        await capture.start()
    try:
        await target.start(max_concurrency)
        try:
            return list(await asyncio.gather(*(one(case) for case in pending)))
        finally:
            await target.stop()
    finally:
        if capture is not None:
            await capture.stop()
