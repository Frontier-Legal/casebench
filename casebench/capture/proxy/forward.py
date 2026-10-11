"""Forward each request to its route's upstream, stream the reply back, record the exchange."""

import contextlib
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx2
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse
from starlette.routing import Route as StarletteRoute

from casebench.capture.proxy.redact import redact_url
from casebench.capture.proxy.routes import Route
from casebench.capture.proxy.sse import parse_events
from casebench.capture.recorder import Recorder
from casebench.capture.step import HttpExchange

# RFC 9110 section 7.6.1: connection-specific headers a proxy must not forward.
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
NOT_FORWARDED = HOP_BY_HOP | {"host", "content-length", "accept-encoding"}
NOT_RETURNED = HOP_BY_HOP | {"content-length", "content-encoding"}

Prepare = Callable[[Any], Any]


def _json(raw: bytes) -> Any:
    try:
        return json.loads(raw) if raw else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def make_app(routes: list[Route], recorder: Recorder, prepare: dict[str, Prepare]) -> Starlette:
    """`prepare` maps a route name to its parser's request hook, such as asking for usage."""
    by_name = {route.name: route for route in routes}
    client = httpx2.AsyncClient(timeout=None)

    async def forward(request: Request) -> Response:
        route = by_name.get(request.path_params["route"])
        if route is None:
            return PlainTextResponse(f"no route {request.path_params['route']!r}", status_code=404)
        url = f"{route.upstream.rstrip('/')}/{request.path_params['path']}"
        if request.url.query:
            url = f"{url}?{request.url.query}"
        raw = await request.body()
        body = _json(raw)
        hook = prepare.get(route.name)
        if hook is not None and body is not None:
            body = hook(body)
            raw = json.dumps(body).encode()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in NOT_FORWARDED}
        headers["accept-encoding"] = "identity"
        started = time.time()
        upstream = await client.send(
            client.build_request(request.method, url, headers=headers, content=raw), stream=True
        )
        chunks: list[bytes] = []

        async def relay() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_raw():
                    chunks.append(chunk)
                    yield chunk
            finally:
                await upstream.aclose()
                ended = time.time()
                content = b"".join(chunks)
                streamed = "text/event-stream" in upstream.headers.get("content-type", "")
                recorder.add(
                    HttpExchange(
                        method=request.method,
                        url=redact_url(url),
                        request_body=body,
                        status=upstream.status_code,
                        response_body=None if streamed else _json(content),
                        response_events=parse_events(content) if streamed else None,
                        route=route.name,
                        started=started,
                        ended=ended,
                        duration_ms=(ended - started) * 1000,
                    ),
                    request.headers.get("traceparent"),
                    request.path_params.get("worker"),
                )

        returned = {k: v for k, v in upstream.headers.items() if k.lower() not in NOT_RETURNED}
        return StreamingResponse(relay(), status_code=upstream.status_code, headers=returned)

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        yield
        await client.aclose()

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    return Starlette(
        routes=[
            StarletteRoute("/w/{worker}/{route}/{path:path}", forward, methods=methods),
            StarletteRoute("/{route}/{path:path}", forward, methods=methods),
        ],
        lifespan=lifespan,
    )
