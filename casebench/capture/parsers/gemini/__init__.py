"""Read Gemini API generateContent calls, streamed or not, into model-call steps.

Gemini may omit function-call ids; a call without one is paired with its result by the
function's name.
"""

import re
from typing import Any, ClassVar

from casebench.capture.sizes import content_size
from casebench.capture.step import HttpExchange, Step, StepKind, ToolCall, ToolResult

METHOD = re.compile(r"/models/([^/:]+):(generateContent|streamGenerateContent)")


def _tool_results(request: Any) -> list[ToolResult]:
    results: list[ToolResult] = []
    for content in (request or {}).get("contents", []):
        for part in content.get("parts") or []:
            answer = part.get("functionResponse")
            if answer:
                key = answer.get("id") or answer["name"]
                results.append(ToolResult(id=key, size=content_size(answer.get("response", {}))))
    return results


def _read(chunks: list[Any]) -> tuple[str | None, int | None, int | None, list[ToolCall]]:
    model = prompt = completion = None
    tools: list[ToolCall] = []
    for chunk in chunks:
        model = chunk.get("modelVersion") or model
        usage = chunk.get("usageMetadata") or {}
        prompt = usage.get("promptTokenCount", prompt)
        completion = usage.get("candidatesTokenCount", completion)
        for candidate in chunk.get("candidates") or []:
            for part in (candidate.get("content") or {}).get("parts") or []:
                call = part.get("functionCall")
                if call:
                    key = call.get("id") or call["name"]
                    tools.append(ToolCall(id=key, name=call["name"], arguments=call.get("args")))
    return model, prompt, completion, tools


class Parser:
    hosts: ClassVar[list[str]] = ["generativelanguage.googleapis.com"]
    packages: ClassVar[list[str]] = ["google-genai", "google-generativeai", "@google/genai"]
    default_route: ClassVar[dict[str, str]] = {
        "name": "gemini",
        "upstream": "https://generativelanguage.googleapis.com",
        "env": "GOOGLE_GEMINI_BASE_URL",
    }

    def parse(self, exchange: HttpExchange) -> list[Step]:
        method = METHOD.search(exchange.url)
        if method is None:
            return []
        if exchange.response_events is not None:
            chunks = exchange.response_events
        else:
            chunks = [exchange.response_body or {}]
        model, prompt, completion, tools = _read(chunks)
        return [
            Step(
                kind=StepKind.LLM,
                provider="gemini",
                model=model or method.group(1),
                input_tokens=prompt,
                output_tokens=completion,
                requested_tools=tools,
                tool_results=_tool_results(exchange.request_body),
                started=exchange.started,
                ended=exchange.ended,
                duration_ms=exchange.duration_ms,
            )
        ]
