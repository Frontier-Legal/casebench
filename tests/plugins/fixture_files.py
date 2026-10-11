"""Files the plugin tests write: a working parser, its samples, a mixed corpus."""

import json
import sys
from pathlib import Path

NATIONAL_PARSER = """from typing import ClassVar

from casebench.capture.step import HttpExchange, Step, StepKind


class Parser:
    hosts: ClassVar[list[str]] = ["llm.national.example"]

    def parse(self, exchange: HttpExchange) -> list[Step]:
        usage = (exchange.response_body or {}).get("usage", {})
        return [Step(kind=StepKind.LLM, model=exchange.request_body["model"],
                     input_tokens=usage.get("in"), output_tokens=usage.get("out"))]
"""


def _call(model: str, tokens_in: int, tokens_out: int) -> dict:
    return {
        "method": "POST",
        "url": "https://llm.national.example/v1/generate",
        "status": 200,
        "request_body": {"model": model, "turns": []},
        "response_body": {"output": "...", "usage": {"in": tokens_in, "out": tokens_out}},
    }


NATIONAL_SAMPLES = {
    "plain.json": {
        "exchange": _call("national-large", 812, 96),
        "expected": [
            {"kind": "llm", "model": "national-large", "input_tokens": 812, "output_tokens": 96}
        ],
    },
    # The parser above drops the call's duration, so this sample does not match.
    "with-duration.json": {
        "exchange": {**_call("national-small", 10, 2), "duration_ms": 40.0},
        "expected": [
            {
                "kind": "llm",
                "model": "national-small",
                "input_tokens": 10,
                "output_tokens": 2,
                "duration_ms": 40.0,
            }
        ],
    },
}


def write_decisions(folder: Path) -> None:
    decisions = [
        {
            "id": "tr-1",
            "jurisdiction": "tr",
            "court": "Yargıtay 9. HD",
            "date": "2024-05-02",
            "text": "Davacı, E.2023/1 K.2024/2 sayılı karara dayanır. HÜKÜM: Bozulmasına.",
        },
        {
            "id": "nl-1",
            "jurisdiction": "nl",
            "court": "Hoge Raad",
            "date": "2024-06-07",
            "text": "Zie ECLI:NL:HR:2024:123. BESLISSING: De Hoge Raad verwerpt het beroep.",
        },
    ]
    for decision in decisions:
        (folder / f"{decision['id']}.json").write_text(
            json.dumps(decision, ensure_ascii=False), encoding="utf-8"
        )


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
