"""The reference builder contract: where a case's answer key comes from."""

from typing import Any, Protocol, runtime_checkable

from casebench.core.case import Case


@runtime_checkable
class ReferenceBuilder(Protocol):
    def build(self, source: Any, *, task: str, metrics: list[str]) -> Case:
        """A case whose reference facts each point at their evidence."""
        ...
