"""Where each proxy route forwards, which parser reads it, and the variable that points at it."""

from casebench.core.model import Record
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


class Route(Record):
    """`http://127.0.0.1:<port>/<name>/...` forwards to `upstream/...`.

    A backend route with no parser names where its responses hold document ids
    (`doc_ids`, JSONPath) and, for a rerank, where its requests hold them (`doc_ids_in`).
    """

    name: str
    upstream: str
    parser: str | None = None
    env: str | None = None
    env_suffix: str = ""
    step: str = "retrieval"
    doc_ids: str | None = None
    doc_ids_in: str | None = None

    def base_url(self, port: int) -> str:
        return f"http://127.0.0.1:{port}/{self.name}{self.env_suffix}"


def default_routes() -> list[Route]:
    """The route each installed parser declares for its upstream's default base URL."""
    kind = kind_named("parser")
    routes: list[Route] = []
    for item in registry.available(kind):
        parser = registry.load(kind, item.name, item.source)()
        declared = getattr(parser, "default_route", None)
        if declared is not None:
            routes.append(Route.model_validate({**declared, "parser": item.name}))
    return routes


def environment(routes: list[Route], port: int) -> dict[str, str]:
    """The variables that point each client at its route."""
    return {route.env: route.base_url(port) for route in routes if route.env}
