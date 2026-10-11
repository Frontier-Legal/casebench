"""Read OpenAI-compatible Chat Completions calls, streamed or not, into model-call steps."""

import json
from typing import Any, ClassVar

from casebench.capture.sizes import content_size
from casebench.capture.step import HttpExchange, Step, StepKind, ToolCall, ToolResult


def _arguments(raw: str) -> Any:
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return raw


def _tool_results(request: Any) -> list[ToolResult]:
    return [
        ToolResult(id=message["tool_call_id"], size=content_size(message.get("content", "")))
        for message in (request or {}).get("messages", [])
        if message.get("role") == "tool" and "tool_call_id" in message
    ]


def _from_body(body: dict[str, Any]) -> tuple[str | None, int | None, int | None, list]:
    usage = body.get("usage") or {}
    message = ((body.get("choices") or [{}])[0]).get("message") or {}
    tools = [
        ToolCall(
            id=call["id"],
            name=call["function"]["name"],
            arguments=_arguments(call["function"].get("arguments", "")),
        )
        for call in message.get("tool_calls") or []
    ]
    return body.get("model"), usage.get("prompt_tokens"), usage.get("completion_tokens"), tools


def _from_chunks(chunks: list[Any]) -> tuple[str | None, int | None, int | None, list]:
    model = prompt = completion = None
    calls: dict[int, dict[str, str]] = {}
    for chunk in chunks:
        model = chunk.get("model") or model
        usage = chunk.get("usage") or {}
        prompt = usage.get("prompt_tokens", prompt)
        completion = usage.get("completion_tokens", completion)
        for choice in chunk.get("choices") or []:
            for call in (choice.get("delta") or {}).get("tool_calls") or []:
                slot = calls.setdefault(call["index"], {"id": "", "name": "", "arguments": ""})
                slot["id"] = call.get("id") or slot["id"]
                function = call.get("function") or {}
                slot["name"] = function.get("name") or slot["name"]
                slot["arguments"] += function.get("arguments") or ""
    tools = [
        ToolCall(id=c["id"], name=c["name"], arguments=_arguments(c["arguments"]))
        for _, c in sorted(calls.items())
    ]
    return model, prompt, completion, tools


class Parser:
    hosts: ClassVar[list[str]] = ["api.openai.com"]
    default_route: ClassVar[dict[str, str]] = {
        "name": "openai",
        "upstream": "https://api.openai.com",
        "env": "OPENAI_BASE_URL",
        "env_suffix": "/v1",
    }

    def prepare(self, body: Any) -> Any:
        """Ask a stream to end with its usage, so its tokens are known (decision 0019)."""
        if isinstance(body, dict) and body.get("stream"):
            options = dict(body.get("stream_options") or {})
            options.setdefault("include_usage", True)
            return {**body, "stream_options": options}
        return body

    def parse(self, exchange: HttpExchange) -> list[Step]:
        if not exchange.url.split("?")[0].rstrip("/").endswith("/chat/completions"):
            return []
        if exchange.response_events is not None:
            model, prompt, completion, tools = _from_chunks(exchange.response_events)
        else:
            model, prompt, completion, tools = _from_body(exchange.response_body or {})
        return [
            Step(
                kind=StepKind.LLM,
                provider="openai",
                model=model or (exchange.request_body or {}).get("model"),
                input_tokens=prompt,
                output_tokens=completion,
                requested_tools=tools,
                tool_results=_tool_results(exchange.request_body),
                started=exchange.started,
                ended=exchange.ended,
                duration_ms=exchange.duration_ms,
            )
        ]
