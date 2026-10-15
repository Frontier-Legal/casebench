"""The perimeter: which hosts a run may call, and the redirects it refuses (decision 0046).

A run may call loopback, the hosts its config names for the target, the judges, the
extraction models, the corpora and the capture routes, and the hosts under `network: allow:`.
Every client Casebench sends through asks `check` before a request leaves, and refuses a
response that redirects to another host. Setup commands, which choose the hosts, run with no
perimeter.
"""

import ipaddress
from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx2
from pydantic import Field

from casebench import keys
from casebench.core.model import Record

ALLOW_HINT = "if the run may call it, add it under `network: allow:` in casebench.yaml"
LOOPBACK_NAMES = {"localhost"}
# The headers that carry a credential (RFC 9110 section 11.6.2 and 11.7.2, and the API-key
# headers the model providers document); each value sent is scrubbed from what a run writes.
CREDENTIAL_HEADERS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "x-goog-api-key",
}


class NetworkConfig(Record):
    """The `network:` section of casebench.yaml: hosts a run may call besides those the
    config names for the target, the judges, the extraction models, the corpora and the
    capture routes."""

    allow: list[str] = Field(default_factory=list)


class HostRefused(Exception):
    """A call outside the perimeter, or a redirect to another host: the run stops."""


def host_of(url: str) -> str:
    """The host a URL names, in lower case and without its port."""
    return (urlsplit(url).hostname or "").lower()


def _loopback(host: str) -> bool:
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Perimeter:
    """`*.example.com` allows every host under example.com, and not example.com itself."""

    def __init__(self, hosts: Iterable[str]) -> None:
        self.hosts = frozenset(host.lower().strip() for host in hosts if host)

    def allows(self, host: str) -> bool:
        host = host.lower()
        if _loopback(host) or host in self.hosts:
            return True
        return any(entry.startswith("*.") and host.endswith(entry[1:]) for entry in self.hosts)


_active: Perimeter | None = None


def enforce(perimeter: Perimeter) -> None:
    """Refuse every host outside `perimeter` until `release`."""
    global _active
    _active = perimeter


def release() -> None:
    global _active
    _active = None


def check(url: str) -> None:
    """Raise when a perimeter is enforced and does not allow the URL's host."""
    host = host_of(url)
    if _active is not None and not _active.allows(host):
        raise HostRefused(
            f"Casebench refused a call to {host}, which casebench.yaml does not name; {ALLOW_HINT}"
        )


def check_redirect(url: str, status: int, location: str | None) -> None:
    """Raise when a response redirects to another host than the one it came from."""
    if not 300 <= status < 400 or not location:
        return
    there = host_of(urljoin(url, location))
    if there and there != host_of(url):
        raise HostRefused(
            f"Casebench refused a redirect from {host_of(url)} to {there}: a run never follows "
            "a redirect to another host"
        )


def note_credentials(headers: Any) -> None:
    """Keep each credential a call carries, so nothing a run writes holds it."""
    for name, value in headers.items():
        if name.lower() in CREDENTIAL_HEADERS and value:
            scheme, _, token = value.partition(" ")
            keys.hide(token if token and scheme.isalpha() and " " not in token else value)


def _on_request(request: httpx2.Request) -> None:
    check(str(request.url))
    note_credentials(request.headers)


def _on_response(response: httpx2.Response) -> None:
    check_redirect(
        str(response.request.url), response.status_code, response.headers.get("location")
    )


async def _on_request_async(request: httpx2.Request) -> None:
    _on_request(request)


async def _on_response_async(response: httpx2.Response) -> None:
    _on_response(response)


def client(**options: Any) -> httpx2.Client:
    """An httpx2 client that keeps to the perimeter."""
    hooks = {"request": [_on_request], "response": [_on_response]}
    return httpx2.Client(event_hooks=hooks, **options)


def async_client(**options: Any) -> httpx2.AsyncClient:
    """An async httpx2 client that keeps to the perimeter."""
    hooks = {"request": [_on_request_async], "response": [_on_response_async]}
    return httpx2.AsyncClient(event_hooks=hooks, **options)
