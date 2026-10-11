"""Send a provider's request over HTTP; the only place Casebench's own model calls leave."""

from typing import Any

import httpx2

from casebench.providers.interface import HttpRequest


def send(request: HttpRequest) -> tuple[int, Any]:
    """No timeout of Casebench's own: a judge's reply takes as long as the provider needs."""
    with httpx2.Client(timeout=None) as client:
        response = client.request(
            request.method, request.url, headers=request.headers, json=request.body
        )
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text
