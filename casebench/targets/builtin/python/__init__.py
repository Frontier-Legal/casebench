"""The python target: call a function in this process once per case."""

import asyncio
import importlib
import inspect
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from casebench.core.model import Record
from casebench.targets.answer import Answer, CitationParser, to_answer


class PythonConfig(Record):
    type: str = "python"
    entry: str
    max_concurrency: int = 1


def load_entry(entry: str) -> Callable[..., Any]:
    """`module:function`, imported with the working directory on the path."""
    module_name, _, attribute = entry.partition(":")
    if not module_name or not attribute:
        raise ValueError(f"entry {entry!r} must look like module:function")
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    function = getattr(importlib.import_module(module_name), attribute)
    if not callable(function):
        raise TypeError(f"{entry} is not callable")
    return function


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


class Target:
    def __init__(self, **config: Any) -> None:
        self.config = PythonConfig.model_validate(config)
        self.function: Callable[..., Any] | None = None

    async def start(self) -> None:
        self.function = load_entry(self.config.entry)

    async def answer(
        self, inputs: Mapping[str, Any], parse_citations: CitationParser | None = None
    ) -> Answer:
        if self.function is None:
            await self.start()
        assert self.function is not None
        value = await call(self.function, accepted(self.function, inputs))
        return to_answer(value, parse_citations)

    async def stop(self) -> None:
        self.function = None
