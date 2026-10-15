"""Forward each request to its route's upstream, stream the reply back, record the exchange."""

import contextlib
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response, StreamingResponse
from starlette.routing import Route as StarletteRoute

from casebench import network
from casebench.capture.otlp.decode import decode
from casebench.capture.proxy.redact import redact_url
from casebench.capture.proxy.routes import Route
from casebench.capture.proxy.sse import parse_events
from casebench.capture.recorder import Recorder
from casebench.capture.redirect import FOLLOWED
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
    """`prepare` maps a route name to its parser's request hook, such as asking for usage. A
    call outside the perimeter, or a redirect to another host, is answered with 403 and kept
    on the recorder, which stops the run (decision 0046)."""
    by_name = {route.name: route for route in routes}
    client = network.async_client(timeout=None)

    async def forward(request: Request) -> Response:
        if "netloc" in request.path_params:
            # A Python agent's call, to the host its own code chose (decision 0044).
            scheme, route = request.path_params["scheme"], None
            if scheme not in ("http", "https"):
                return PlainTextResponse(f"no scheme {scheme!r}", status_code=404)
            base = f"{scheme}://{request.path_params['netloc']}"
        else:
            route = by_name.get(request.path_params["route"])
            if route is None:
                missing = request.path_params["route"]
                return PlainTextResponse(f"no route {missing!r}", status_code=404)
            base = route.upstream
        url = f"{base.rstrip('/')}/{request.path_params['path']}"
        if request.url.query:
            url = f"{url}?{request.url.query}"
        raw = await request.body()
        body = _json(raw)
        hook = prepare.get(route.name) if route is not None else None
        if hook is not None and body is not None:
            body = hook(body)
            raw = json.dumps(body).encode()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in NOT_FORWARDED}
        headers["accept-encoding"] = "identity"
        # Wall-clock times order the steps; the duration comes from the monotonic clock, which
        # on Windows is fine enough to time a fast local call, as the wall clock is not.
        started, begun = time.time(), time.perf_counter()
        try:
            upstream = await client.send(
                client.build_request(request.method, url, headers=headers, content=raw),
                stream=True,
            )
        except network.HostRefused as refused:
            recorder.refuse(str(refused))
            return PlainTextResponse(str(refused), status_code=403)
        chunks: list[bytes] = []

        async def relay() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream.aiter_raw():
                    chunks.append(chunk)
                    yield chunk
            finally:
                await upstream.aclose()
                ended, took = time.time(), time.perf_counter() - begun
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
                        route=route.name if route is not None else None,
                        started=started,
                        ended=ended,
                        duration_ms=took * 1000,
                    ),
                    request.headers.get("traceparent"),
                    request.path_params.get("worker"),
                )

        returned = {k: v for k, v in upstream.headers.items() if k.lower() not in NOT_RETURNED}
        return StreamingResponse(relay(), status_code=upstream.status_code, headers=returned)

    async def traces(request: Request) -> Response:
        """OTLP/HTTP trace export; an empty success reply is what exporters expect."""
        content_type = request.headers.get("content-type", "application/x-protobuf")
        recorder.add_spans(decode(await request.body(), content_type))
        if "json" in content_type:
            return Response("{}", media_type="application/json")
        return Response(b"", media_type="application/x-protobuf")

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        yield
        await client.aclose()

    methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    return Starlette(
        routes=[
            StarletteRoute("/v1/traces", traces, methods=["POST"]),
            StarletteRoute(
                f"/w/{{worker}}/{FOLLOWED}/{{scheme}}/{{netloc}}/{{path:path}}",
                forward,
                methods=methods,
            ),
            StarletteRoute(
                f"/{FOLLOWED}/{{scheme}}/{{netloc}}/{{path:path}}", forward, methods=methods
            ),
            StarletteRoute("/w/{worker}/{route}/{path:path}", forward, methods=methods),
            StarletteRoute("/{route}/{path:path}", forward, methods=methods),
        ],
        lifespan=lifespan,
    )
