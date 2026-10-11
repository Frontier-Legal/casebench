"""The task type contract: what the AI is asked to do and how its output is read."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TaskType(Protocol):
    @property
    def input_fields(self) -> tuple[str, ...]:
        """The case inputs the target receives, by name."""
        ...

    @property
    def default_metrics(self) -> tuple[str, ...]:
        """The metrics a case of this type gets when it names none."""
        ...
