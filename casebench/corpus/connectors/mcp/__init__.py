"""The mcp connector: any MCP server with a search tool and a fetch tool."""

import asyncio
import contextlib
import json
import sys
import threading
from collections.abc import Awaitable, Callable
from concurrent.futures import Future
from typing import Any, TypeVar

import mcp
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

# The SDK's own client factory keeps its timeouts for long-lived response streams; it lives in
# a private module, and the header test fails first if it moves.
from mcp.shared._httpx_utils import create_mcp_http_client
from pydantic import Field

from casebench.core.model import Record
from casebench.corpus.mapping import every, record_fields
from casebench.targets.placeholders import expand_env

Result = TypeVar("Result")


class McpCorpusConfig(Record):
    """`command` starts a server over stdio; `url` reaches one over Streamable HTTP, sending
    `headers` (with `${VAR}` read from the environment) on every request. Tool arguments may
    hold `{text}`, `{limit}` and `{id}`."""

    command: list[str] | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    search_tool: str = ""
    search_arguments: dict[str, Any] = Field(default_factory=lambda: {"query": "{text}"})
    search_ids: str = "$"
    fetch_tool: str = ""
    fetch_arguments: dict[str, Any] = Field(default_factory=lambda: {"id": "{id}"})
    fields: dict[str, str] = Field(default_factory=dict)


def _fill(arguments: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    filled: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, str) and value.startswith("{") and value[1:-1] in values:
            filled[key] = values[value[1:-1]]
        else:
            filled[key] = value
    return filled


def _json_or_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _payload(result: Any) -> Any:
    """A tool's structured content, or the JSON in its first text block. A tool that returns
    a string has it wrapped as `{"result": "..."}`; the string is read as JSON when it is."""
    structured = getattr(result, "structured_content", None) or getattr(
        result, "structuredContent", None
    )
    if isinstance(structured, dict) and set(structured) == {"result"}:
        inner = structured["result"]
        return _json_or_text(inner) if isinstance(inner, str) else inner
    if structured is not None:
        return structured
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text is not None:
            return _json_or_text(text)
    return None


class Connector:
    """Keeps one MCP session open for the connector's life, in a single task on a background
    event loop, because the SDK's session must be opened and closed by the same task."""

    def __init__(self, server: Any = None, **options: Any) -> None:
        self.config = McpCorpusConfig.model_validate(options)
        target = server or self.config.url
        if target is None and self.config.command:
            command, *arguments = self.config.command
            # The server's log goes to the terminal Casebench was started from, even when
            # sys.stderr has been replaced by something without a file descriptor.
            log = sys.__stderr__ or sys.stderr
            target = stdio_client(mcp.StdioServerParameters(command=command, args=arguments), log)
        if target is None:
            raise ValueError("an mcp corpus needs a command or a url")
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.ready = threading.Event()
        self.requests: asyncio.Queue[Any] | None = None
        self.session = asyncio.run_coroutine_threadsafe(self._serve(target), self.loop)
        while not self.ready.wait(timeout=None if self.session.done() else 0.05):
            if self.session.done():
                self.session.result()

    async def _serve(self, target: Any) -> None:
        self.requests = asyncio.Queue()
        async with contextlib.AsyncExitStack() as stack:
            if isinstance(target, str) and self.config.headers:
                http = create_mcp_http_client(headers=expand_env(self.config.headers))
                await stack.enter_async_context(http)
                target = streamable_http_client(target, http_client=http)
            client = await stack.enter_async_context(mcp.Client(target))
            self.ready.set()
            while (request := await self.requests.get()) is not None:
                call, answer = request
                try:
                    answer.set_result(await call(client))
                except Exception as error:
                    answer.set_exception(error)

    def _ask(self, call: Callable[[Any], Awaitable[Result]]) -> Result:
        answer: Future[Result] = Future()
        assert self.requests is not None
        self.loop.call_soon_threadsafe(self.requests.put_nowait, (call, answer))
        return answer.result()

    def _call(self, tool: str, arguments: dict[str, Any]) -> Any:
        return _payload(self._ask(lambda client: client.call_tool(tool, arguments)))

    def tools(self) -> list[tuple[str, str, dict[str, Any]]]:
        """Each tool's name, description and input schema."""
        listed = self._ask(lambda client: client.list_tools())
        return [(t.name, t.description or "", dict(t.input_schema or {})) for t in listed.tools]

    def search_raw(self, text: str, limit: int) -> Any:
        arguments = _fill(self.config.search_arguments, {"text": text, "limit": limit})
        return self._call(self.config.search_tool, arguments)

    def fetch_raw(self, decision_id: str) -> Any:
        arguments = _fill(self.config.fetch_arguments, {"id": decision_id})
        return self._call(self.config.fetch_tool, arguments)

    def search(self, text: str, limit: int) -> list[str]:
        found = every(self.config.search_ids, self.search_raw(text, limit))
        return [str(item) for item in found][:limit]

    def fetch(self, decision_id: str) -> dict[str, Any]:
        return record_fields(self.fetch_raw(decision_id), self.config.fields)

    def close(self) -> None:
        if self.requests is not None:
            self.loop.call_soon_threadsafe(self.requests.put_nowait, None)
        self.session.result()
        self.loop.call_soon_threadsafe(self.loop.stop)
