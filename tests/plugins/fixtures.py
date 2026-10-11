"""Plugins that exist only for the tests: a national model API's parser and provider."""

from typing import Any, ClassVar

from casebench.capture.step import HttpExchange, Step, StepKind
from casebench.providers.interface import Completion, HttpRequest, Message


class NationalApiParser:
    hosts: ClassVar[list[str]] = ["llm.national.example"]

    def parse(self, exchange: HttpExchange) -> list[Step]:
        usage = exchange.response_body["usage"]
        return [
            Step(
                kind=StepKind.LLM,
                model=exchange.request_body["model"],
                input_tokens=usage["in"],
                output_tokens=usage["out"],
                duration_ms=exchange.duration_ms,
            )
        ]


class NationalApiProvider:
    family = "national"
    api_key_env = "NATIONAL_API_KEY"

    def request(self, messages: list[Message], model: str, api_key: str) -> HttpRequest:
        return HttpRequest(
            method="POST",
            url="https://llm.national.example/v1/generate",
            headers={"Authorization": f"Bearer {api_key}"},
            body={"model": model, "turns": [m.model_dump() for m in messages]},
        )

    def parse(self, status: int, body: Any) -> Completion:
        if status != 200:
            raise RuntimeError(f"the API answered {status}")
        return Completion(
            text=body["output"],
            input_tokens=body["usage"]["in"],
            output_tokens=body["usage"]["out"],
        )
