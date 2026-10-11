"""Plugins that exist only for the tests: two jurisdictions, a model API and its parser."""

import re
from datetime import date
from typing import Any, ClassVar

from casebench.adapters.interface import Citation, CitationKind
from casebench.capture.step import HttpExchange, Step, StepKind
from casebench.corpus.record import DecisionRecord
from casebench.providers.interface import Completion, HttpRequest, Message


class _RegexAdapter:
    code = ""
    pattern = re.compile("")
    ruling = ""
    levels: ClassVar[dict[str, str]] = {}

    def key(self, match: re.Match[str]) -> str:
        return match.group(0)

    def citations(self, text: str) -> list[Citation]:
        return [
            Citation(
                text=m.group(0),
                start=m.start(),
                end=m.end(),
                kind=CitationKind.DECISION,
                key=self.key(m),
            )
            for m in self.pattern.finditer(text)
        ]

    def operative_part(self, record: DecisionRecord) -> tuple[int, int] | None:
        start = record.text.find(self.ruling)
        return None if start < 0 else (start, len(record.text))

    def court_level(self, court: str) -> str | None:
        return self.levels.get(court)

    def statute_version(self, key: str, on: date) -> str | None:
        return None


class TrAdapter(_RegexAdapter):
    code = "tr"
    pattern = re.compile(r"E\.(\d{4})/(\d+) K\.(\d{4})/(\d+)")
    ruling = "HÜKÜM"
    levels: ClassVar[dict[str, str]] = {"Yargıtay 9. HD": "appellate"}

    def key(self, match: re.Match[str]) -> str:
        return "E{}/{}-K{}/{}".format(*match.groups())


class NlAdapter(_RegexAdapter):
    code = "nl"
    pattern = re.compile(r"ECLI:NL:[A-Z]+:\d{4}:[A-Z0-9]+")
    ruling = "BESLISSING"
    levels: ClassVar[dict[str, str]] = {"Hoge Raad": "supreme"}


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
