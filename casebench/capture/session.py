"""Start the recording proxy for a run and point every client at it."""

import json
import os
from urllib.parse import urlsplit

from casebench import keys, network
from casebench.capture.backend import backend_step
from casebench.capture.config import CaptureConfig, routes_for
from casebench.capture.corpus_routes import corpus_routes
from casebench.capture.functions import STEP_FUNCTIONS, StepFunction
from casebench.capture.interface import CaptureParser
from casebench.capture.proxy.forward import Prepare, make_app
from casebench.capture.proxy.routes import Route, default_routes, environment
from casebench.capture.proxy.server import ProxyServer
from casebench.capture.recorder import Recorder
from casebench.capture.redirect import FOLLOW
from casebench.capture.searches import search_step
from casebench.capture.step import HttpExchange, Step
from casebench.corpus.binding import CorpusConfig
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named

TRACES_ENDPOINT = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"


def traces_endpoint(port: int) -> str:
    return f"http://127.0.0.1:{port}/v1/traces"


# Read by workers to put their own path in each variable (decision 0020).
PROXY = "CASEBENCH_PROXY"
# Each variable the session points at the proxy, with the value it had before, so a Python
# worker can keep the project's own (decision 0044).
SHADOWED = "CASEBENCH_SHADOWED"
PROXY_VARIABLES = "CASEBENCH_PROXY_VARIABLES"


def _to_set_upstream(route: Route, port: int) -> Route:
    """A route through a variable forwards to the base URL that variable already has here, in
    the shell or a .env file named under `keys`, not to the parser's default host: a key is
    sent only to the host the project chose (decision 0044). A variable that already points
    at this proxy, as after exporting the lines `casebench proxy env` prints, names no host,
    so the route keeps its own upstream, as when the variable is unset."""
    if route.env is None:
        return route
    current = keys.get(route.env)
    if not current:
        return route
    parts = urlsplit(current)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return route
    if port and parts.port == port and network.is_loopback(parts.hostname or ""):
        return route
    update = {"upstream": f"{parts.scheme}://{parts.netloc}", "env_suffix": parts.path.rstrip("/")}
    return route.model_copy(update=update)


class CaptureSession:
    """For one run: the proxy, the recorder, and the variables that point clients at it."""

    def __init__(
        self,
        routes: list[Route],
        port: int = 0,
        functions: list[StepFunction] | None = None,
        traces: bool = False,
    ) -> None:
        self.routes = {route.name: route for route in routes}
        self.functions = functions or []
        self.traces = traces
        self.port = port
        self.recorder = Recorder()
        self.parsers: dict[str, CaptureParser] = {
            route.name: registry.load(kind_named("parser"), route.parser)()
            for route in routes
            if route.parser
        }
        kind = kind_named("parser")
        self.all_parsers: list[CaptureParser] = [
            registry.load(kind, item.name, item.source)() for item in registry.available(kind)
        ]
        self.server: ProxyServer | None = None
        self.env: dict[str, str] = {}
        self._previous: dict[str, str | None] = {}

    def hook_for(self, route: Route | None, url: str) -> Prepare | None:
        """The request hook of the parser that reads a call, found as `parse` finds it: by the
        call's route, or for a followed call the route at its host, or else the parser whose
        API the call is (decision 0044)."""
        route = route or self._route_at(url)
        if route is not None:
            return getattr(self.parsers.get(route.name), "prepare", None)
        for parser in self.all_parsers:
            reads = getattr(parser, "reads", None)
            if reads is not None and reads(url):
                return getattr(parser, "prepare", None)
        return None

    async def start(self) -> dict[str, str]:
        self.routes = {
            name: _to_set_upstream(route, self.port) for name, route in self.routes.items()
        }
        app = make_app(list(self.routes.values()), self.recorder, self.hook_for)
        self.server = ProxyServer(app, self.port)
        self.port = await self.server.start()
        self.env = environment(list(self.routes.values()), self.port)
        proxy = f"http://127.0.0.1:{self.port}"
        # A Python worker sends every call here, to the host it chose, and keeps the project's
        # own value of each variable a parser's default route sets; a route the config gives
        # its own upstream keeps its variable, as for an agent that runs as a command or a
        # server (decision 0044).
        self.env[FOLLOW] = proxy
        defaults = {route.name: route.upstream for route in default_routes()}
        shadowed = [
            route.env
            for route in self.routes.values()
            if route.env and defaults.get(route.name) == route.upstream
        ]
        self.env[SHADOWED] = json.dumps({name: os.environ.get(name) for name in shadowed})
        self.env[PROXY] = proxy
        self.env[PROXY_VARIABLES] = ",".join(name for name in self.env if name != PROXY)

        if self.traces:
            self.env[TRACES_ENDPOINT] = traces_endpoint(self.port)
        if self.functions:
            self.env[STEP_FUNCTIONS] = json.dumps(
                [f.model_dump(mode="json") for f in self.functions]
            )
        for name, value in self.env.items():
            self._previous[name] = os.environ.get(name)
            os.environ[name] = value
        return self.env

    def parse(self, exchange: HttpExchange) -> list[Step]:
        """A call through a route is read by the route's parser or as a backend step. A call
        a Python agent made to a host of its choosing is read by the route for that host, or
        by the first parser whose API it is: each parser reads only its API's own paths, or as
        a search of a store whose API is known."""
        route = self.routes.get(exchange.route or "") or self._route_at(exchange.url)
        if route is not None:
            parser = self.parsers.get(route.name)
            return parser.parse(exchange) if parser else [backend_step(exchange, route)]
        if exchange.route is not None:
            return []
        for parser in self.all_parsers:
            try:
                steps = parser.parse(exchange)
            except Exception:
                continue
            if steps:
                return steps
        # A search of a store whose API Casebench knows, by its path (decision 0061).
        searched = search_step(exchange)
        return [searched] if searched is not None else []

    def _route_at(self, url: str) -> Route | None:
        host = urlsplit(url).netloc
        return next((r for r in self.routes.values() if urlsplit(r.upstream).netloc == host), None)

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


def session_for(
    capture: CaptureConfig | None, corpora: dict[str, CorpusConfig] | None = None
) -> CaptureSession:
    """The session the config's `capture:` section describes, or the defaults without one,
    with a route at each corpus the agent may search itself (decision 0044)."""
    routes = routes_for(capture)
    routes += corpus_routes(corpora or {}, routes)
    if capture is None:
        return CaptureSession(routes)
    return CaptureSession(routes, capture.port, capture.functions, capture.traces)
