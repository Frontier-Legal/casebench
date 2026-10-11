"""The target contract: how a case reaches the AI under test."""

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Target(Protocol):
    def answer(self, inputs: Mapping[str, Any]) -> Any:
        """The target's answer to one case's inputs."""
        ...
