"""Send an agent's calls to a captured upstream through the recording proxy, in its worker only.

A client created with a literal base URL ignores the variables that point other clients at
the proxy. The Python target's worker rewrites such a call's URL inside httpx2, httpx and
requests, the HTTP libraries the common model SDKs send through, before the call leaves the
process. Production never loads the worker, so it never runs this (decision 0044).
"""

import importlib
import json
from typing import Any

# The variable that carries `{upstream: proxy route}` to the worker.
REDIRECTS = "CASEBENCH_REDIRECTS"
# The openai 3.x and anthropic 1.x SDKs send through httpx2; earlier ones, and many agents'
# own clients, through httpx (both read on 2026-10-14). The two share these names.
HTTPX_MODULES = ("httpx2", "httpx")


def rewritten(url: str, redirects: dict[str, str]) -> str | None:
    """The proxy's URL for a call to a captured upstream, or None for any other call."""
    for upstream, routed in redirects.items():
        base = upstream.rstrip("/")
        if url == base or url.startswith((f"{base}/", f"{base}?")):
            return routed.rstrip("/") + url[len(base) :]
    return None


def _httpx(name: str, redirects: dict[str, str]) -> None:
    try:
        module: Any = importlib.import_module(name)
    except ImportError:
        return
    sync = module.HTTPTransport.handle_request
    asynchronous = module.AsyncHTTPTransport.handle_async_request

    def move(request: Any) -> None:
        new = rewritten(str(request.url), redirects)
        if new is not None:
            request.url = module.URL(new)
            request.headers["host"] = request.url.netloc.decode("ascii")

    def handle_request(self: Any, request: Any) -> Any:
        move(request)
        return sync(self, request)

    async def handle_async_request(self: Any, request: Any) -> Any:
        move(request)
        return await asynchronous(self, request)

    module.HTTPTransport.handle_request = handle_request
    module.AsyncHTTPTransport.handle_async_request = handle_async_request


def _requests(redirects: dict[str, str]) -> None:
    try:
        from requests.adapters import HTTPAdapter
    except ImportError:
        return
    send = HTTPAdapter.send

    def moved(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        new = rewritten(str(request.url), redirects)
        if new is not None:
            request.url = new
            request.headers.pop("Host", None)
        return send(self, request, *args, **kwargs)

    HTTPAdapter.send = moved  # type: ignore[method-assign]


def install(raw: str | None) -> None:
    """Rewrite calls to each captured upstream, when the run captures any."""
    if not raw:
        return
    redirects = json.loads(raw)
    for name in HTTPX_MODULES:
        _httpx(name, redirects)
    _requests(redirects)
