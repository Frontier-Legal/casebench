"""Wrap functions the config names so each call records a step with its document ids."""

import dataclasses
import functools
import inspect
import json
import time
from collections.abc import Callable
from typing import Any

from jsonpath_ng.ext.parser import parse as jsonpath

from casebench.capture.context import record
from casebench.capture.step import NO_DIAGNOSTIC, Step, StepKind
from casebench.core.model import Record
from casebench.loading import import_location, resolve, split_entry

# Set by the capture session for worker processes (decision 0022).
STEP_FUNCTIONS = "CASEBENCH_STEP_FUNCTIONS"


class StepFunction(Record):
    """`capture.functions` in casebench.yaml."""

    function: str
    step: StepKind = StepKind.RERANK
    name: str | None = None
    doc_ids_in: str | None = None
    doc_ids_out: str | None = None


def _plain(value: Any) -> Any:
    """Dataclasses, pydantic models and plain objects as their fields, for JSONPath."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in dataclasses.asdict(value).items()}
    dump = getattr(value, "model_dump", None)
    if callable(dump) and not isinstance(value, type):
        return _plain(dump())
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_plain(v) for v in value]
    if hasattr(value, "__dict__") and not callable(value):
        return {k: _plain(v) for k, v in vars(value).items() if not k.startswith("_")}
    return value


def _ids(expression: str | None, document: Any) -> list[str]:
    if expression is None:
        return []
    return [str(match.value) for match in jsonpath(expression).find(document)]


def _step(
    spec: StepFunction, arguments: dict[str, Any], result: Any, started: float, begun: float
) -> Step:
    """`started` orders the step by the wall clock; `begun` times it by the monotonic one."""
    ended = time.time()
    document = {"arguments": _plain(arguments), "result": _plain(result)}
    ids_out = _ids(spec.doc_ids_out, document)
    return Step(
        kind=spec.step,
        name=spec.name or spec.function.rsplit(":", 1)[-1],
        doc_ids_in=_ids(spec.doc_ids_in, document),
        doc_ids_out=ids_out,
        started=started,
        ended=ended,
        duration_ms=(time.perf_counter() - begun) * 1000,
        note=None if ids_out else NO_DIAGNOSTIC,
    )


def wrap(spec: StepFunction, original: Callable[..., Any]) -> Callable[..., Any]:
    signature = inspect.signature(original)

    def bound(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        try:
            return dict(signature.bind(*args, **kwargs).arguments)
        except TypeError:
            return {"args": list(args), **kwargs}

    if inspect.iscoroutinefunction(original):

        @functools.wraps(original)
        async def wrapped_async(*args: Any, **kwargs: Any) -> Any:
            started, begun = time.time(), time.perf_counter()
            result = await original(*args, **kwargs)
            record(_step(spec, bound(args, kwargs), result, started, begun))
            return result

        return wrapped_async

    @functools.wraps(original)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        started, begun = time.time(), time.perf_counter()
        result = original(*args, **kwargs)
        record(_step(spec, bound(args, kwargs), result, started, begun))
        return result

    return wrapped


def install(specs: list[StepFunction]) -> None:
    """Replace each named function on the object that holds it; a missing name stops here."""
    for spec in specs:
        location, attribute, is_file = split_entry(spec.function)
        owner, name = resolve(import_location(location, is_file), attribute)
        original = getattr(owner, name, None)
        if not callable(original):
            raise LookupError(f"capture.functions names {spec.function}, which is not a function")
        setattr(owner, name, wrap(spec, original))


def specs_from_environment(value: str | None) -> list[StepFunction]:
    return [StepFunction.model_validate(item) for item in json.loads(value)] if value else []
