"""The organisation a request works for, which every row it writes carries (decision 0066).

A workbench on one machine, and a firm's own team server, have one organisation; the hosted
service has many, and the database admits only the rows of the one set here.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# The one organisation a workbench on an engineer's machine, or a self-hosted server, has.
LOCAL = "local"
_ORGANISATION: ContextVar[str] = ContextVar("casebench_organisation", default=LOCAL)


def current() -> str:
    return _ORGANISATION.get()


def enter(organisation: str) -> None:
    """For the rest of this request: its middleware sets it once, before any route runs."""
    _ORGANISATION.set(organisation)


@contextmanager
def as_organisation(organisation: str) -> Iterator[None]:
    """Work done for another organisation than the request's, such as signing a person in."""
    token = _ORGANISATION.set(organisation)
    try:
        yield
    finally:
        _ORGANISATION.reset(token)


# Given a request, the organisation it is for; None for the one a server keeps by default.
Resolver = Callable[[Request], str | None]


class Organisations(BaseHTTPMiddleware):
    """Sets the request's organisation before any route reads or writes, from who is calling;
    a workbench with no resolver has only the local one."""

    def __init__(self, app: Any, resolve: Resolver | None) -> None:
        super().__init__(app)
        self.resolve = resolve

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        found = await run_in_threadpool(self.resolve, request) if self.resolve else None
        enter(found or LOCAL)
        return await call_next(request)
