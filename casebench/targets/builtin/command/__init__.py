"""The command target: run a program once per case and read its standard output."""

import asyncio
from collections.abc import Mapping
from typing import Any

from casebench.core.model import Record
from casebench.targets.answer import Answer, CitationParser, to_answer
from casebench.targets.placeholders import fill_args


class CommandFailed(RuntimeError):
    """The command exited non-zero for one case."""


class CommandConfig(Record):
    type: str = "command"
    run: str
    max_concurrency: int = 1


class Target:
    def __init__(self, **config: Any) -> None:
        self.config = CommandConfig.model_validate(config)

    async def start(self) -> None:
        return None

    async def answer(
        self, inputs: Mapping[str, Any], parse_citations: CitationParser | None = None
    ) -> Answer:
        process = await asyncio.create_subprocess_exec(
            *fill_args(self.config.run, inputs),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            lines = stderr.decode("utf-8", "replace").strip().splitlines()
            last = f": {lines[-1]}" if lines else ""
            raise CommandFailed(f"the command exited with {process.returncode}{last}")
        return to_answer(stdout.decode("utf-8").strip(), parse_citations)

    async def stop(self) -> None:
        return None
