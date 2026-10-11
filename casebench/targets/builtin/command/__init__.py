"""The command target: run a program once per case and read its standard output."""

import asyncio
import os
from collections.abc import Mapping
from typing import Any

from casebench.capture.context import current_traceparent
from casebench.core.model import Record
from casebench.targets.answer import Answer, to_answer
from casebench.targets.placeholders import fill_args


class CommandFailed(RuntimeError):
    """The command exited non-zero for one case."""


class CommandConfig(Record):
    type: str = "command"
    run: str
    max_concurrency: int = 1


def _with_trace_context() -> dict[str, str]:
    """The run's environment plus the case's trace context, the OpenTelemetry carrier."""
    traceparent = current_traceparent()
    return {**os.environ, "TRACEPARENT": traceparent} if traceparent else dict(os.environ)


class Target:
    def __init__(self, **config: Any) -> None:
        self.config = CommandConfig.model_validate(config)

    async def start(self, slots: int = 1) -> None:
        return None

    async def answer(self, inputs: Mapping[str, Any]) -> Answer:
        process = await asyncio.create_subprocess_exec(
            *fill_args(self.config.run, inputs),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_with_trace_context(),
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            lines = stderr.decode("utf-8", "replace").strip().splitlines()
            last = f": {lines[-1]}" if lines else ""
            raise CommandFailed(f"the command exited with {process.returncode}{last}")
        return to_answer(stdout.decode("utf-8").strip())

    async def stop(self) -> None:
        return None
