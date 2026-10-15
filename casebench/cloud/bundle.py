"""What crosses the line to a team server: which files of a run and of a suite are sent.

With --traces, steps go too, as ids and numbers only (decision 0059).
"""

import json
import re
from pathlib import Path
from typing import Any

from casebench.capture.step import Step
from casebench.report.calibration import REVIEWS_FILE
from casebench.report.preferences import PREFERENCES_FILE
from casebench.report.render import REPORT_FILE
from casebench.runs.log import RESULTS_FILE, RUN_FILE, SCORES_DIR, Result, RunLog
from casebench.suites.freeze import MANIFEST_FILE, SUITE_FILE

# A run's files that are sent; anything else in its folder stays, the judge's replies above all.
RUN_FILES = (RUN_FILE, RESULTS_FILE, REPORT_FILE, REVIEWS_FILE, PREFERENCES_FILE)
# Lines people add on either side; merged, never replaced.
MERGED = (REVIEWS_FILE, PREFERENCES_FILE)
SCORE_SET = re.compile(rf"^{SCORES_DIR}/[A-Za-z0-9_-]+\.jsonl$")
SUITE_FILES = (MANIFEST_FILE, SUITE_FILE)
# Ids a run or a suite may have to be stored under its own folder on the server.
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
# What a step keeps with --traces: what it was, what it cost and when, never what it said.
STEP_FIELDS = (
    "kind",
    "name",
    "provider",
    "model",
    "doc_ids_in",
    "doc_ids_out",
    "input_tokens",
    "output_tokens",
    "result_size",
    "started",
    "ended",
    "duration_ms",
)


class Refused(ValueError):
    """A file, path or id that does not cross the line."""


def safe_id(value: str) -> str:
    if not SAFE_ID.match(value) or ".." in value:
        raise Refused(f"{value!r} is not an id a run or a suite can be stored under")
    return value


def run_file(path: str) -> bool:
    """Whether a path inside a run's folder is one that is sent."""
    return path in RUN_FILES or bool(SCORE_SET.match(path))


def traced(step: Step) -> dict[str, Any]:
    """The step as ids and numbers: no tool arguments, no notes, no message content."""
    kept = step.model_dump(mode="json", include=set(STEP_FIELDS))
    kept["requested_tools"] = [{"id": c.id, "name": c.name} for c in step.requested_tools]
    kept["tool_results"] = [{"id": r.id, "size": r.size} for r in step.tool_results]
    return kept


def result_line(result: Result, traces: bool) -> str:
    sent = result.model_dump(mode="json", exclude={"steps"})
    sent["steps"] = [traced(step) for step in result.steps] if traces else []
    return json.dumps(sent, ensure_ascii=False)


def run_files(log: RunLog, traces: bool) -> dict[str, str]:
    """The run's files as they are sent, by their path in its folder."""
    files: dict[str, str] = {}
    for name in RUN_FILES:
        path = log.folder / name
        if not path.is_file():
            continue
        if name == RESULTS_FILE:
            files[name] = "".join(result_line(r, traces) + "\n" for r in log.results())
        else:
            files[name] = path.read_text(encoding="utf-8")
    for path in log.score_sets():
        files[f"{SCORES_DIR}/{path.name}"] = path.read_text(encoding="utf-8")
    return files


def suite_files(folder: Path) -> dict[str, str]:
    return {name: (folder / name).read_text(encoding="utf-8") for name in SUITE_FILES}


def merged(ours: str, theirs: str) -> str:
    """Every line of both, ours first, each once."""
    seen: dict[str, None] = {}
    for line in (*ours.splitlines(), *theirs.splitlines()):
        if line.strip():
            seen.setdefault(line, None)
    return "".join(line + "\n" for line in seen)
