"""Call a Python agent's entry point with a case's inputs."""

import asyncio
import inspect
from collections.abc import Callable, Mapping
from typing import Any

from casebench.loading import DEFAULT_FUNCTION, load_entry, split_entry

__all__ = ["DEFAULT_FUNCTION", "accepted", "call", "load_entry", "split_entry"]


def accepted(function: Callable[..., Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """All inputs for `**kwargs`; otherwise only the ones the function names."""
    parameters = inspect.signature(function).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return dict(inputs)
    return {name: value for name, value in inputs.items() if name in parameters}


async def call(function: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
    """Await coroutines, join generators' chunks, run plain functions in a thread."""
    if inspect.isasyncgenfunction(function):
        return "".join([str(chunk) async for chunk in function(**kwargs)])
    if inspect.iscoroutinefunction(function):
        return await function(**kwargs)
    if inspect.isgeneratorfunction(function):
        return await asyncio.to_thread(lambda: "".join(str(c) for c in function(**kwargs)))
    value = await asyncio.to_thread(function, **kwargs)
    return await value if inspect.isawaitable(value) else value
