"""Make a case's trace context current in the agent's own OpenTelemetry, if it has one."""

import importlib.util
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def agent_trace_context(traceparent: str | None) -> Iterator[None]:
    """Spans the agent starts while answering then carry the case's trace id (decision 0023).
    Casebench does not depend on OpenTelemetry; an agent without it is left alone."""
    if not traceparent or importlib.util.find_spec("opentelemetry") is None:
        yield
        return
    from opentelemetry import context, propagate

    token = context.attach(propagate.extract({"traceparent": traceparent}))
    try:
        yield
    finally:
        context.detach(token)
