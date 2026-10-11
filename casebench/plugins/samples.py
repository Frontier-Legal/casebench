"""Read a plugin's conformance samples, and the report every suite returns."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SuiteResult:
    """What one kind's conformance suite found on a plugin's samples."""

    problems: list[str] = field(default_factory=list)
    figure: float | None = None
    samples: int = 0


def sample_files(samples: Path) -> list[Path]:
    """Every `*.json` sample except `config.json`, in name order."""
    return sorted(path for path in samples.glob("*.json") if path.name != "config.json")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ratio(passed: int, total: int) -> float | None:
    return passed / total if total else None
