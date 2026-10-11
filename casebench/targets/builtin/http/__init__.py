"""The http target: send each case to an endpoint, optionally started by Casebench."""

import asyncio
import subprocess
from collections.abc import Mapping
from typing import Any

import httpx
from jsonpath_ng.ext.parser import parse as jsonpath
from pydantic import Field

from casebench.capture.context import current_traceparent
from casebench.core.model import Record
from casebench.targets.answer import Answer, CitationParser, to_answer
from casebench.targets.placeholders import expand_env, fill_json, split_command

# Decision 0017: a start that completes between polls is seen at most this late.
READY_POLL_SECONDS = 0.1


class StartFailed(RuntimeError):
    pass


class HttpConfig(Record):
    type: str = "http"
    url: str
    method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any
    answer: str
    citations: str | None = None
    documents: str | None = None
    start: str | None = None
    timeout_s: float | None = None
    max_concurrency: int = 1


def first(expression: str, document: Any) -> Any:
    matches = jsonpath(expression).find(document)
    if not matches:
        raise ValueError(f"the response has nothing at {expression}")
    return matches[0].value


def every(expression: str | None, document: Any) -> list[Any] | None:
    if expression is None:
        return None
    return [match.value for match in jsonpath(expression).find(document)]


def _with_trace_context(headers: dict[str, str]) -> dict[str, str]:
    traceparent = current_traceparent()
    return {**headers, "traceparent": traceparent} if traceparent else headers


class Target:
    def __init__(self, **config: Any) -> None:
        self.config = HttpConfig.model_validate(config)
        self.process: subprocess.Popen[bytes] | None = None
        self.client = httpx.AsyncClient(timeout=self.config.timeout_s)

    async def start(self) -> None:
        if self.config.start is None:
            return
        self.process = subprocess.Popen(split_command(self.config.start))
        await self._wait_until_ready()

    async def _wait_until_ready(self) -> None:
        """Until the endpoint answers anything, the start command exits, or the user stops."""
        while True:
            if self.process is not None and self.process.poll() is not None:
                raise StartFailed(
                    f"the start command exited with {self.process.returncode} "
                    f"before {self.config.url} answered"
                )
            try:
                await self.client.request("HEAD", self.config.url)
                return
            except httpx.TransportError:
                await asyncio.sleep(READY_POLL_SECONDS)

    async def answer(
        self, inputs: Mapping[str, Any], parse_citations: CitationParser | None = None
    ) -> Answer:
        response = await self.client.request(
            self.config.method,
            self.config.url,
            headers=_with_trace_context(expand_env(self.config.headers)),
            json=fill_json(self.config.body, inputs),
        )
        response.raise_for_status()
        document = response.json()
        value: dict[str, Any] = {"answer": first(self.config.answer, document)}
        citations = every(self.config.citations, document)
        if citations is not None:
            value["citations"] = citations
        value["documents"] = every(self.config.documents, document) or []
        return to_answer(value, parse_citations)

    async def stop(self) -> None:
        await self.client.aclose()
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
        self.process = None
