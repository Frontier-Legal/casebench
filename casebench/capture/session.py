"""Start the recording proxy for a run and point every client at it."""

import os
from typing import Any

from casebench.capture.backend import backend_step
from casebench.capture.interface import CaptureParser
from casebench.capture.proxy.forward import make_app
from casebench.capture.proxy.routes import Route, environment
from casebench.capture.proxy.server import ProxyServer
from casebench.capture.recorder import Recorder
from casebench.capture.step import HttpExchange, Step
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


class CaptureSession:
    """For one run: the proxy, the recorder, and the variables that point clients at it."""

    def __init__(self, routes: list[Route], port: int = 0) -> None:
        self.routes = {route.name: route for route in routes}
        self.port = port
        self.recorder = Recorder()
        self.parsers: dict[str, CaptureParser] = {
            route.name: registry.load(kind_named("parser"), route.parser)()
            for route in routes
            if route.parser
        }
        self.server: ProxyServer | None = None
        self.env: dict[str, str] = {}
        self._previous: dict[str, str | None] = {}

    async def start(self) -> dict[str, str]:
        prepare: dict[str, Any] = {
            name: parser.prepare  # type: ignore[attr-defined]
            for name, parser in self.parsers.items()
            if hasattr(parser, "prepare")
        }
        app = make_app(list(self.routes.values()), self.recorder, prepare)
        self.server = ProxyServer(app, self.port)
        self.port = await self.server.start()
        self.env = environment(list(self.routes.values()), self.port)
        for name, value in self.env.items():
            self._previous[name] = os.environ.get(name)
            os.environ[name] = value
        return self.env

    def parse(self, exchange: HttpExchange) -> list[Step]:
        route = self.routes.get(exchange.route or "")
        if route is None:
            return []
        parser = self.parsers.get(route.name)
        return parser.parse(exchange) if parser else [backend_step(exchange, route)]

    async def stop(self) -> None:
        for name, value in self._previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self._previous.clear()
        if self.server is not None:
            await self.server.stop()
            self.server = None
