"""Send each call a Python agent makes through the recording proxy, to the host it chose.

The Python target's worker rewrites every outgoing call in httpx2, httpx and requests, the
HTTP libraries the common model SDKs send through, to the proxy's follow path. The path
carries the call's own scheme and host, and the proxy forwards it there unchanged. A call
always reaches the host the agent's code chose, whatever base URL its settings give, and a
key never reaches another host. Production never loads the worker, so it never runs this
(decision 0044).
"""

import importlib
from typing import Any
from urllib.parse import urlsplit

# The variable that carries the worker's proxy address, such as http://127.0.0.1:5000/w/0.
FOLLOW = "CASEBENCH_FOLLOW"
# The path segment under which the proxy forwards a call to the host the path names.
FOLLOWED = "~"
# The openai 3.x and anthropic 1.x SDKs send through httpx2; earlier ones, and many agents'
# own clients, through httpx (both read on 2026-10-14). The two share these names.
HTTPX_MODULES = ("httpx2", "httpx")


def followed(url: str, proxy: str) -> str | None:
    """The proxy's URL for a call, or None for a call to the proxy itself."""
    parts, own = urlsplit(url), urlsplit(proxy)
    if parts.scheme not in ("http", "https") or parts.netloc == own.netloc:
        return None
    query = f"?{parts.query}" if parts.query else ""
    path = parts.path or "/"
    return f"{proxy.rstrip('/')}/{FOLLOWED}/{parts.scheme}/{parts.netloc}{path}{query}"


def _httpx(name: str, proxy: str) -> None:
    try:
        module: Any = importlib.import_module(name)
    except ImportError:
        return
    sync = module.HTTPTransport.handle_request
    asynchronous = module.AsyncHTTPTransport.handle_async_request

    def move(request: Any) -> None:
        new = followed(str(request.url), proxy)
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


def _requests(proxy: str) -> None:
    try:
        from requests.adapters import HTTPAdapter
    except ImportError:
        return
    send = HTTPAdapter.send

    def moved(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        new = followed(str(request.url), proxy)
        if new is not None:
            request.url = new
            request.headers.pop("Host", None)
        return send(self, request, *args, **kwargs)

    HTTPAdapter.send = moved  # type: ignore[method-assign]


def install(proxy: str | None) -> None:
    """Send every call through the proxy, when the run captures."""
    if not proxy:
        return
    for name in HTTPX_MODULES:
        _httpx(name, proxy)
    _requests(proxy)
