"""The exporter contract: write cases and scores into another tool."""

from typing import Protocol, runtime_checkable

from casebench.core.score import Score
from casebench.runs.log import RunLog


@runtime_checkable
class Exporter(Protocol):
    def export(self, log: RunLog, scores: list[Score]) -> None: ...
