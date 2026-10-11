"""The stub each plugin kind starts from. Every method says what to implement."""

CLASS_NAMES = {
    "adapter": "Adapter",
    "connector": "Connector",
    "parser": "Parser",
    "provider": "Provider",
    "task": "Task",
    "reference": "Builder",
    "target": "Target",
    "metric": "Metric",
    "exporter": "Exporter",
}

STUBS = {
    "adapter": """from datetime import date

from casebench.adapters.interface import Citation
from casebench.corpus.record import DecisionRecord


class Adapter:
    code = "{name}"

    def citations(self, text: str) -> list[Citation]:
        raise NotImplementedError("find decision and statute citations in the text")

    def operative_part(self, record: DecisionRecord) -> tuple[int, int] | None:
        raise NotImplementedError("locate the ruling in the decision text")

    def court_level(self, court: str) -> str | None:
        raise NotImplementedError("map a court name to its level")

    def statute_version(self, key: str, on: date) -> str | None:
        return None
""",
    "connector": """from collections.abc import Iterable
from typing import Any


class Connector:
    def __init__(self, **options: Any) -> None:
        self.options = options

    def list_ids(self) -> Iterable[str]:
        raise NotImplementedError("list every decision id in the store")

    def fetch(self, decision_id: str) -> dict[str, Any]:
        raise NotImplementedError("return one decision keyed by the decision record's fields")
""",
    "parser": """from casebench.capture.step import HttpExchange, Step


class Parser:
    hosts = ["api.{name}.example"]

    def parse(self, exchange: HttpExchange) -> list[Step]:
        raise NotImplementedError("turn one exchange into steps")
""",
    "provider": """from typing import Any

from casebench.providers.interface import Completion, HttpRequest, Message


class Provider:
    family = "{name}"
    api_key_env = "{env}_API_KEY"

    def request(self, messages: list[Message], model: str, api_key: str) -> HttpRequest:
        raise NotImplementedError("build the HTTP request for these messages")

    def parse(self, status: int, body: Any) -> Completion:
        raise NotImplementedError("read the completion out of the response body")
""",
    "task": """class Task:
    input_fields = ("question",)
    default_metrics: tuple[str, ...] = ()
""",
    "reference": """from typing import Any

from casebench.core.case import Case


class Builder:
    def build(self, source: Any, *, task: str, metrics: list[str]) -> Case:
        raise NotImplementedError("build a case whose facts point at their evidence")
""",
    "target": """from collections.abc import Mapping
from typing import Any


class Target:
    def answer(self, inputs: Mapping[str, Any]) -> Any:
        raise NotImplementedError("send the case to the AI under test")
""",
    "metric": """from casebench.core.case import Case
from casebench.core.score import Direction, ScoreKind
from casebench.metrics.base import Verdict
from casebench.runs.log import Result


class Metric:
    name = "{name}"
    version = "1"
    kind = ScoreKind.CODE
    direction = Direction.HIGHER

    def judge(self, case: Case, result: Result) -> Verdict:
        raise NotImplementedError("score one output")
""",
    "exporter": """from casebench.core.score import Score
from casebench.runs.log import RunLog


class Exporter:
    def export(self, log: RunLog, scores: list[Score]) -> None:
        raise NotImplementedError("write the run into the other tool")
""",
}

SAMPLES_README = """# Conformance samples

`casebench plugin test <path>` runs this plugin's conformance suite on the files here.
The format for each kind is in the docstring of its suite: `casebench.adapters.conformance`,
`casebench.corpus.conformance`, `casebench.capture.conformance` or
`casebench.providers.conformance`. Use only data you are allowed to redistribute.
"""

CONFORMANCE_TEST = """from pathlib import Path

from casebench.plugins.conformance import run


def test_meets_its_conformance_suite():
    report = run(Path(__file__).resolve().parents[{depth}]{subpath})
    assert report.passed, report.problems
"""
