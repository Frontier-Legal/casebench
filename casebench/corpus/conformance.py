"""Conformance for corpus connectors, measured as the share of required fields present.

`samples/config.json` holds `{"options": {...}}` for the connector; an option value
starting with `./` is a path relative to the samples folder.
"""

from pathlib import Path
from typing import Any

from casebench.corpus.record import REQUIRED_FIELDS
from casebench.plugins.samples import SuiteResult, ratio, read_json


def options_for(samples: Path) -> dict[str, Any]:
    config = samples / "config.json"
    options = read_json(config).get("options", {}) if config.is_file() else {}
    return {
        key: str((samples / value).resolve())
        if isinstance(value, str) and value.startswith("./")
        else value
        for key, value in options.items()
    }


def check(connector: Any, samples: Path) -> SuiteResult:
    result = SuiteResult()
    present = 0
    try:
        ids = list(connector.list_ids())
    except Exception as error:
        result.problems.append(f"list_ids(): {type(error).__name__}: {error}")
        return result
    if not ids:
        result.problems.append("list_ids() returned no decisions from the samples")
    for decision_id in ids:
        result.samples += 1
        try:
            raw = connector.fetch(decision_id)
        except Exception as error:
            result.problems.append(f"fetch({decision_id!r}): {type(error).__name__}: {error}")
            continue
        if not isinstance(raw, dict):
            result.problems.append(f"fetch({decision_id!r}) must return a mapping")
            continue
        present += sum(1 for name in REQUIRED_FIELDS if raw.get(name) not in (None, ""))
    result.figure = ratio(present, len(REQUIRED_FIELDS) * result.samples)
    return result
