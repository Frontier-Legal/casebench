"""Conformance for model providers, measured as the share of recorded responses parsed.

A sample is `{"messages": [...], "model": "...", "expected_request": {"method", "url"},
"response": {"status", "body"}, "expected": <completion>}`. It runs offline: the
provider only builds the request and reads the recorded response.
"""

from pathlib import Path

from casebench.plugins.samples import SuiteResult, ratio, read_json, sample_files
from casebench.providers.interface import Completion, HttpRequest, Message, ModelProvider

PLACEHOLDER_KEY = "conformance-placeholder-key"


def check(provider: ModelProvider, samples: Path) -> SuiteResult:
    result = SuiteResult()
    parsed = 0
    for path in sample_files(samples):
        result.samples += 1
        sample = read_json(path)
        messages = [Message.model_validate(item) for item in sample["messages"]]
        try:
            request = provider.request(messages, sample["model"], PLACEHOLDER_KEY)
            completion = provider.parse(sample["response"]["status"], sample["response"]["body"])
        except Exception as error:
            result.problems.append(f"{path.name}: {type(error).__name__}: {error}")
            continue
        if not isinstance(request, HttpRequest) or not isinstance(completion, Completion):
            result.problems.append(f"{path.name}: request() and parse() return the wrong types")
            continue
        wanted = sample.get("expected_request", {})
        for field in ("method", "url"):
            if field in wanted and getattr(request, field) != wanted[field]:
                result.problems.append(f"{path.name}: request {field} is {getattr(request, field)}")
        parsed += completion == Completion.model_validate(sample["expected"])
    result.figure = ratio(parsed, result.samples)
    return result
