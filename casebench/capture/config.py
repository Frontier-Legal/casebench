"""The `capture:` section of casebench.yaml: the proxy's port and its routes."""

from typing import Any

from pydantic import Field

from casebench.capture.functions import StepFunction
from casebench.capture.proxy.routes import Route, default_routes
from casebench.core.model import Record


class CaptureConfig(Record):
    """`port: 0` lets the operating system choose; name a port for an agent already running.
    `traces: true` points the OpenTelemetry exporter of agents Casebench starts at it.
    `content: true` keeps the arguments of tool calls and named functions in stored steps,
    which are dropped otherwise (decision 0062)."""

    port: int = 0
    routes: list[dict[str, Any]] = Field(default_factory=list)
    functions: list[StepFunction] = Field(default_factory=list)
    traces: bool = False
    content: bool = False


def routes_for(capture: CaptureConfig | None) -> list[Route]:
    """The parsers' default routes, with the config's fields laid over a route of the same
    name, and the config's new routes added."""
    merged = {route.name: route.model_dump() for route in default_routes()}
    for route in capture.routes if capture else []:
        merged[route["name"]] = {**merged.get(route["name"], {}), **route}
    return [Route.model_validate(fields) for fields in merged.values()]
