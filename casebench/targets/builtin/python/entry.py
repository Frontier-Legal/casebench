"""Load a Python agent's entry point and call it with a case's inputs."""

import asyncio
import hashlib
import importlib
import importlib.util
import inspect
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import Any

DEFAULT_FUNCTION = "answer"


def split_entry(entry: str) -> tuple[str, str, bool]:
    """(module or file, function, is a file). The function follows the last colon, so a
    Windows path's drive letter (`C:\\agents\\agent.py:answer`) stays in the path."""
    if entry.endswith(".py"):
        return entry, DEFAULT_FUNCTION, True
    location, _, function = entry.rpartition(":")
    if not location or not function:
        raise ValueError(f"entry {entry!r} must look like module:function or agent.py")
    return location, function, location.endswith(".py")


def load_entry(entry: str) -> Callable[..., Any]:
    """`module:function`, or `path/to/agent.py[:function]` with `answer` as the default."""
    location, attribute, is_file = split_entry(entry)
    if is_file:
        module = _module_from_file(Path(location))
    else:
        cwd = str(Path.cwd())
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        module = importlib.import_module(location)
    function = getattr(module, attribute, None)
    if not callable(function):
        raise TypeError(f"{entry} has no function {attribute!r}")
    return function


def _module_from_file(path: Path) -> ModuleType:
    """Import a script by path; its folder goes on the path so its own imports work."""
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{path} does not exist")
    name = f"casebench_agent_{hashlib.sha256(str(resolved).encode()).hexdigest()}"
    if name in sys.modules:
        return sys.modules[name]
    if str(resolved.parent) not in sys.path:
        sys.path.insert(0, str(resolved.parent))
    spec = importlib.util.spec_from_file_location(name, resolved)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
