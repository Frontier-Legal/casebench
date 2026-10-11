"""Tie every captured step to the case that caused it."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from casebench.capture.step import Step


@dataclass
class CaseCapture:
    case_id: str
    traceparent: str | None = None
    steps: list[Step] = field(default_factory=list)


_current: ContextVar[CaseCapture | None] = ContextVar("casebench_case", default=None)


@contextmanager
def capturing(case_id: str, traceparent: str | None = None) -> Iterator[CaseCapture]:
    """Steps recorded inside this block belong to this case, even with other cases
    running at the same time, because each asyncio task and thread gets its own copy."""
    capture = CaseCapture(case_id, traceparent)
    token = _current.set(capture)
    try:
        yield capture
    finally:
        _current.reset(token)


def record(step: Step) -> bool:
    """Attach a step to the running case; False when no case is running."""
    capture = _current.get()
    if capture is None:
        return False
    capture.steps.append(step)
    return True


def current_traceparent() -> str | None:
    """The running case's trace context, to pass on to an agent outside this process."""
    capture = _current.get()
    return capture.traceparent if capture is not None else None
