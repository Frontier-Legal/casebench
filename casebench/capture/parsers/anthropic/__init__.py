"""Read Anthropic Messages API calls, streamed or not, into model-call steps."""

import json
from typing import Any, ClassVar

from casebench.capture.sizes import content_size
from casebench.capture.step import HttpExchange, Step, StepKind, ToolCall, ToolResult


def _tool_results(request: Any) -> list[ToolResult]:
    results: list[ToolResult] = []
    for message in (request or {}).get("messages", []):
        if message.get("role") != "user" or not isinstance(message.get("content"), list):
            continue
        for block in message["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                size = content_size(block.get("content", ""))
                results.append(ToolResult(id=block["tool_use_id"], size=size))
    return results


def _from_message(message: dict[str, Any]) -> tuple[str | None, int | None, int | None, list]:
    usage = message.get("usage") or {}
    tools = [
        ToolCall(id=block["id"], name=block["name"], arguments=block.get("input"))
        for block in message.get("content") or []
        if block.get("type") == "tool_use"
    ]
    return message.get("model"), usage.get("input_tokens"), usage.get("output_tokens"), tools


def _from_events(events: list[Any]) -> tuple[str | None, int | None, int | None, list]:
    model = input_tokens = output_tokens = None
    blocks: dict[int, dict[str, Any]] = {}
    for event in events:
        kind = event.get("type")
        if kind == "message_start":
            model = event["message"].get("model")
            input_tokens = (event["message"].get("usage") or {}).get("input_tokens")
        elif kind == "content_block_start" and event["content_block"].get("type") == "tool_use":
            block = event["content_block"]
            blocks[event["index"]] = {"id": block["id"], "name": block["name"], "json": ""}
        elif kind == "content_block_delta" and event["delta"].get("type") == "input_json_delta":
            if event["index"] in blocks:
                blocks[event["index"]]["json"] += event["delta"].get("partial_json", "")
        elif kind == "message_delta":
            output_tokens = (event.get("usage") or {}).get("output_tokens", output_tokens)
    tools = [
        ToolCall(id=b["id"], name=b["name"], arguments=json.loads(b["json"]) if b["json"] else {})
        for _, b in sorted(blocks.items())
    ]
    return model, input_tokens, output_tokens, tools


class Parser:
    hosts: ClassVar[list[str]] = ["api.anthropic.com"]
    packages: ClassVar[list[str]] = ["anthropic", "@anthropic-ai/sdk"]
    default_route: ClassVar[dict[str, str]] = {
        "name": "anthropic",
        "upstream": "https://api.anthropic.com",
        "env": "ANTHROPIC_BASE_URL",
    }

    def parse(self, exchange: HttpExchange) -> list[Step]:
        if not exchange.url.rstrip("/").endswith("/v1/messages"):
            return []
        if exchange.response_events is not None:
            model, tokens_in, tokens_out, tools = _from_events(exchange.response_events)
        else:
            model, tokens_in, tokens_out, tools = _from_message(exchange.response_body or {})
        return [
            Step(
                kind=StepKind.LLM,
                provider="anthropic",
                model=model or (exchange.request_body or {}).get("model"),
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                requested_tools=tools,
                tool_results=_tool_results(exchange.request_body),
                started=exchange.started,
                ended=exchange.ended,
                duration_ms=exchange.duration_ms,
            )
        ]
