"""Conformance for capture parsers, measured as the share of recorded calls parsed.

A sample is `{"exchange": <HTTP exchange>, "expected": [<step>, ...]}`.
"""

from pathlib import Path

from casebench.capture.interface import CaptureParser
from casebench.capture.step import HttpExchange, Step
from casebench.plugins.samples import SuiteResult, ratio, read_json, sample_files


def check(parser: CaptureParser, samples: Path) -> SuiteResult:
    result = SuiteResult()
    parsed = 0
    if not parser.hosts:
        result.problems.append("hosts is empty, so no traffic would reach this parser")
    for path in sample_files(samples):
        result.samples += 1
        sample = read_json(path)
        exchange = HttpExchange.model_validate(sample["exchange"])
        expected = [Step.model_validate(step) for step in sample["expected"]]
        try:
            steps = parser.parse(exchange)
        except Exception as error:
            result.problems.append(f"{path.name}: {type(error).__name__}: {error}")
            continue
        if not all(isinstance(step, Step) for step in steps):
            result.problems.append(f"{path.name}: parse() must return Step records")
            continue
        parsed += steps == expected
    result.figure = ratio(parsed, result.samples)
    return result
