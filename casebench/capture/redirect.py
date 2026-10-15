"""Send each call a Python agent makes through the recording proxy, to the host it chose.

The Python target's worker rewrites every outgoing call in httpx2, httpx and requests, the
HTTP libraries the common model SDKs send through, to the proxy's follow path. The path
carries the call's own scheme and host, and the proxy forwards it there unchanged. A call
always reaches the host the agent's code chose, whatever base URL its settings give, and a
key never reaches another host. Production never loads the worker, so it never runs this
(decision 0044).

`cb.instrument()` patches the same libraries in the agent's own process; calls go through
the proxy only while `cb.run` has one running, and are unchanged otherwise (decision 0062).
"""

import importlib
from contextvars import ContextVar
from typing import Any
from urllib.parse import urlsplit

# The variable that carries the worker's proxy address, such as http://127.0.0.1:5000/w/0.
FOLLOW = "CASEBENCH_FOLLOW"
# The path segment under which the proxy forwards a call to the host the path names.
FOLLOWED = "~"
# The openai 3.x and anthropic 1.x SDKs send through httpx2; earlier ones, and many agents'
# own clients, through httpx (both read on 2026-10-14). The two share these names.
HTTPX_MODULES = ("httpx2", "httpx")
# Set while the proxy sends a call upstream, so a proxy in the agent's own process never
# sends its own calls back to itself.
DIRECT: ContextVar[bool] = ContextVar("casebench_direct", default=False)

_proxy: str | None = None
_patched: list[str] = []


def followed(url: str, proxy: str) -> str | None:
    """The proxy's URL for a call, or None for a call to the proxy itself."""
    parts, own = urlsplit(url), urlsplit(proxy)
    if parts.scheme not in ("http", "https") or parts.netloc == own.netloc:
        return None
    query = f"?{parts.query}" if parts.query else ""
    path = parts.path or "/"
    return f"{proxy.rstrip('/')}/{FOLLOWED}/{parts.scheme}/{parts.netloc}{path}{query}"


def _moved(url: str) -> str | None:
    """Where a call goes now: through the proxy while one is followed, else unchanged."""
    if _proxy is None or DIRECT.get():
        return None
    return followed(url, _proxy)


def _httpx(name: str) -> bool:
    try:
        module: Any = importlib.import_module(name)
    except ImportError:
        return False
    sync = module.HTTPTransport.handle_request
    asynchronous = module.AsyncHTTPTransport.handle_async_request

    def move(request: Any) -> None:
        new = _moved(str(request.url))
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
    return True


def _requests() -> bool:
    try:
        from requests.adapters import HTTPAdapter
    except ImportError:
        return False
    send = HTTPAdapter.send

    def moved(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        new = _moved(str(request.url))
        if new is not None:
            request.url = new
            request.headers.pop("Host", None)
        return send(self, request, *args, **kwargs)

    HTTPAdapter.send = moved  # type: ignore[method-assign]
    return True


def patch() -> list[str]:
    """Patch every installed library once; the libraries whose calls can be followed."""
    if not _patched:
        _patched.extend(name for name in HTTPX_MODULES if _httpx(name))
        if _requests():
            _patched.append("requests")
    return list(_patched)


def follow(proxy: str | None) -> None:
    """Send calls through `proxy` from now on, or nowhere new with None."""
    global _proxy
    _proxy = proxy


def install(proxy: str | None) -> None:
    """Send every call through the proxy, when the run captures."""
    if not proxy:
        return
    follow(proxy)
    patch()
