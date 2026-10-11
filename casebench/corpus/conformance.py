"""Conformance for corpus connectors, measured as the share of required fields present."""

from pathlib import Path
from typing import Any

from casebench.corpus.interface import ListingNotSupported, list_ids
from casebench.corpus.record import REQUIRED_FIELDS
from casebench.plugins.samples import SuiteResult, ratio


def check(connector: Any, samples: Path) -> SuiteResult:
    result = SuiteResult()
    present = 0
    try:
        ids = list(list_ids(connector))
    except ListingNotSupported:
        ids = []
        result.problems.append("conformance samples need a connector that can list them")
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
    if ids:
        try:
            found = connector.search(str(connector.fetch(ids[0]).get("text", "")), 1)
            if not isinstance(found, list):
                result.problems.append("search() must return a list of ids")
        except Exception as error:
            result.problems.append(f"search(): {type(error).__name__}: {error}")
    result.figure = ratio(present, len(REQUIRED_FIELDS) * result.samples)
    return result
