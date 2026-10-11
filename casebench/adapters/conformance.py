"""Conformance for jurisdiction adapters, measured as extraction accuracy on samples.

A sample is `{"decision": <decision record>, "expected": {...}}`, where `expected` may
hold `citations` (the keys in order), `operative_part_starts_with` and `court_level`.
Each expected field is one check; accuracy is the share of checks that pass.
"""

from pathlib import Path

from casebench.adapters.interface import Citation, JurisdictionAdapter
from casebench.corpus.record import DecisionRecord
from casebench.plugins.samples import SuiteResult, ratio, read_json, sample_files


def check(adapter: JurisdictionAdapter, samples: Path) -> SuiteResult:
    result = SuiteResult()
    passed = total = 0
    for path in sample_files(samples):
        result.samples += 1
        sample = read_json(path)
        record = DecisionRecord.model_validate(sample["decision"])
        expected = sample.get("expected", {})
        try:
            found = adapter.citations(record.text)
            span = adapter.operative_part(record)
            level = adapter.court_level(record.court)
        except Exception as error:
            result.problems.append(f"{path.name}: {type(error).__name__}: {error}")
            continue
        if not all(isinstance(item, Citation) for item in found):
            result.problems.append(f"{path.name}: citations() must return Citation records")
            continue
        if span is not None and not 0 <= span[0] <= span[1] <= len(record.text):
            result.problems.append(f"{path.name}: operative_part() is outside the text")
            continue
        if "citations" in expected:
            total += 1
            passed += [item.key for item in found] == expected["citations"]
        if "operative_part_starts_with" in expected:
            total += 1
            prefix = expected["operative_part_starts_with"]
            passed += span is not None and record.text[span[0] : span[1]].startswith(prefix)
        if "court_level" in expected:
            total += 1
            passed += level == expected["court_level"]
    result.figure = ratio(passed, total)
    return result
