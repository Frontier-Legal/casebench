"""The target contract: how a case reaches the AI under test."""

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from casebench.targets.answer import Answer, CitationParser


class TargetDidNotStart(RuntimeError):
    """The target could not start, so the run stops before its first case."""


@runtime_checkable
class Target(Protocol):
    """Built from its config, started once per run, asked once per case, stopped at the end.
    `slots` is how many cases the run will send at once."""

    async def start(self, slots: int = 1) -> None: ...

    async def answer(
        self, inputs: Mapping[str, Any], parse_citations: CitationParser | None = None
    ) -> Answer: ...

    async def stop(self) -> None: ...
