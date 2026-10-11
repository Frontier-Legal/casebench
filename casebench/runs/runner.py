"""Send every case of a suite to the target and store each result as it finishes."""

import asyncio
import time

from casebench.capture.context import capturing
from casebench.core.case import Case
from casebench.runs.log import Result, RunLog
from casebench.targets.answer import CitationParser
from casebench.targets.interface import Target


async def ask(case: Case, target: Target, parse_citations: CitationParser | None) -> Result:
    """One case, with the steps captured while it ran. A failure is the case's, not the run's."""
    with capturing(case.id) as capture:
        started = time.perf_counter()
        try:
            answer = await target.answer(case.task.inputs, parse_citations)
        except Exception as error:
            return Result(
                case_id=case.id,
                error=f"{type(error).__name__}: {error}",
                steps=capture.steps,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        return Result(
            case_id=case.id,
            output=answer.text,
            citations=answer.citations,
            documents=answer.documents,
            steps=capture.steps,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


async def run_cases(
    cases: list[Case],
    target: Target,
    log: RunLog,
    *,
    max_concurrency: int = 1,
    parse_citations: CitationParser | None = None,
) -> list[Result]:
    """At most `max_concurrency` cases at once; cases the log already holds are skipped."""
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")
    stored = {result.case_id for result in log.results()}
    pending = [case for case in cases if case.id not in stored]
    slots = asyncio.Semaphore(max_concurrency)

    async def one(case: Case) -> Result:
        async with slots:
            result = await ask(case, target, parse_citations)
        log.append(result)
        return result

    await target.start()
    try:
        return list(await asyncio.gather(*(one(case) for case in pending)))
    finally:
        await target.stop()
