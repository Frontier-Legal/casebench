"""Read the repository's own files for the convention tests."""

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def load_yaml(relative: str) -> Any:
    return yaml.safe_load(text(relative))


def load_json(relative: str) -> Any:
    return json.loads(text(relative))


def workflow(name: str) -> dict[Any, Any]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def all_workflows() -> dict[str, dict[str, Any]]:
    return {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(WORKFLOWS.glob("*.yml"))
    }


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return job.get("steps", [])


def run_lines(job: dict[str, Any]) -> str:
    return "\n".join(step.get("run", "") for step in steps(job))


def uses(job: dict[str, Any]) -> list[str]:
    return [step["uses"] for step in steps(job) if "uses" in step]
