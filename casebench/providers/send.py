"""Send a provider's request over HTTP; the only place Casebench's own model calls leave.

So the perimeter applies here (decision 0046).
"""

import email.utils
import math
import random
import time
from collections.abc import Callable
from typing import Any

import httpx2

from casebench import network
from casebench.providers.interface import HttpRequest

# What the openai 3.29.0 and anthropic 1.13.0 Python SDKs both do by default, read on
# 2026-10-14 (decision 0037): a call times out as theirs do, and is retried as often, as soon,
# for the same answers. How long a `retry-after` each honours is the request's own.
TIMEOUT = httpx2.Timeout(600.0, connect=5.0)
RETRIES = 2
FIRST_WAIT_S = 0.5
LONGEST_WAIT_S = 8.0
JITTER = 0.25
RETRIED = (408, 409, 429)


def _retry_after(response: httpx2.Response | None) -> float | None:
    """The wait the server asks for: `retry-after-ms`, else `retry-after` in seconds or as a
    date."""
    if response is None:
        return None
    headers = response.headers
    for name, scale in (("retry-after-ms", 1000.0), ("retry-after", 1.0)):
        try:
            told = float(headers.get(name, ""))
        except ValueError:
            continue
        if math.isfinite(told):
            return told / scale
    dated = email.utils.parsedate_tz(headers.get("retry-after", ""))
    return None if dated is None else float(email.utils.mktime_tz(dated) - time.time())


def _retried(response: httpx2.Response, longest: float | None) -> bool:
    """As the SDKs decide: never past a wait longer than the provider honours, then the
    server's `x-should-retry`, then the status."""
    told = _retry_after(response)
    if longest is not None and told is not None and told > longest:
        return False
    should = response.headers.get("x-should-retry")
    if should in ("true", "false"):
        return should == "true"
    return response.status_code in RETRIED or response.status_code >= 500


def _wait(retry: int, response: httpx2.Response | None) -> float:
    """The server's wait when it asks for one, else a doubling wait less up to a quarter at
    random."""
    told = _retry_after(response)
    if told is not None and told > 0:
        return told
    return min(FIRST_WAIT_S * 2**retry, LONGEST_WAIT_S) * (1 - JITTER * random.random())


def send(request: HttpRequest, sleep: Callable[[float], None] = time.sleep) -> tuple[int, Any]:
    """A dropped connection, a timeout or a refusal worth retrying is tried again; what still
    fails after the last retry is raised or returned to the provider to report."""
    retry = 0
    while True:
        try:
            with network.client(timeout=TIMEOUT) as client:
                response = client.request(
                    request.method, request.url, headers=request.headers, json=request.body
                )
        except httpx2.TransportError:
            if retry == RETRIES:
                raise
            sleep(_wait(retry, None))
            retry += 1
            continue
        if retry == RETRIES or not _retried(response, request.longest_retry_after_s):
            break
        sleep(_wait(retry, response))
        retry += 1
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text
