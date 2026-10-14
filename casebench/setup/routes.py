"""Turn the clients a scan found into capture routes the proxy can stand in front of (0040)."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from casebench.capture.corpus_routes import ids_path
from casebench.capture.proxy.routes import Route, default_routes
from casebench.corpus.binding import CorpusConfig
from casebench.setup.scan import Client


@dataclass(frozen=True)
class Offer:
    """A route to write for one client, or None with why the client cannot be routed."""

    client: Client
    route: dict[str, Any] | None
    note: str


def _name(host: str, taken: set[str]) -> str:
    """The whole host, as a route name: `api.fireworks.ai` is `api-fireworks-ai`."""
    parts = [part for part in host.lower().replace("_", "-").split(".") if part]
    name = "-".join(parts) or "backend"
    candidate, number = name, 2
    while candidate in taken:
        candidate, number = f"{name}-{number}", number + 1
    return candidate


def _corpus_at(host: str, corpora: dict[str, CorpusConfig]) -> CorpusConfig | None:
    for corpus in corpora.values():
        base = corpus.options.get("base_url") if corpus.connector == "http" else None
        if base and urlsplit(str(base)).hostname == host:
            return corpus
    return None


def offers(clients: list[Client], corpora: dict[str, CorpusConfig]) -> list[Offer]:
    """A model client on its parser's default base URL needs no new route; one that reads
    its base URL from a variable gets a route through that variable; one with a literal base
    URL needs no route when the target is Python, whose worker records each call where it
    goes, and cannot be routed for a command or HTTP target (decision 0044). A backend at a
    corpus's host is recorded by the corpus's own paths: searches as retrievals, fetches as
    documents."""
    defaults = {route.parser: route for route in default_routes()}
    taken = {route.name for route in defaults.values()}
    made: list[Offer] = []
    for client in clients:
        source = client.base_url
        default = defaults.get(client.parser)
        if source is None:
            if default is not None:
                made.append(Offer(client, None, f"its parser's route, through {default.env}"))
            continue
        # A base URL passed to the client overrides the SDK's own variable, so only the
        # variable the code reads it from, or a Python worker, reaches the proxy.
        if source.env is None:
            note = (
                f"fixes its base URL as {source.literal}: recorded as it calls when the target "
                "is Python; a command or HTTP target needs the URL read from a variable"
            )
            made.append(Offer(client, None, note))
            continue
        if default is not None and source.env == default.env:
            made.append(Offer(client, None, f"its parser's route, through {default.env}"))
            continue
        url = source.literal
        if url is None:
            note = f"reads its base URL from {source.env} with no default; add its route by hand"
            made.append(Offer(client, None, note))
            continue
        parts = urlsplit(url)
        host = parts.hostname or ""
        name = _name(host, taken)
        taken.add(name)
        route: dict[str, Any] = {
            "name": name,
            "upstream": f"{parts.scheme}://{parts.netloc}",
            "env": source.env,
            "env_suffix": parts.path.rstrip("/"),
        }
        if client.parser is not None:
            route["parser"] = client.parser
        else:
            corpus = _corpus_at(host, corpora)
            if corpus is None:
                made.append(
                    Offer(
                        client,
                        None,
                        f"a backend at {host}; no corpus is at that host, so its ids are not known",
                    )
                )
                continue
            route |= {
                "step": "retrieval",
                "doc_ids": ids_path(corpus.options),
                "fetch_path": corpus.options.get("fetch_path"),
            }
        Route.model_validate(route)
        made.append(
            Offer(client, route, f"route {name} -> {route['upstream']}, through {source.env}")
        )
    return made
