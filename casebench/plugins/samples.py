"""Read a plugin's conformance samples.

`samples/config.json` holds `{"options": {...}}` for building the plugin; an option
value starting with `./` is a path relative to the samples folder.
"""

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


def options_for(samples: Path) -> dict[str, Any]:
    config = samples / "config.json"
    options = read_json(config).get("options", {}) if config.is_file() else {}
    return {
        key: str((samples / value).resolve())
        if isinstance(value, str) and value.startswith("./")
        else value
        for key, value in options.items()
    }
