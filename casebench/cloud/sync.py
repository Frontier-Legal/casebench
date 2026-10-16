"""Push this machine's runs and their suites, and pull lawyers' decisions back (decision 0059)."""

from dataclasses import dataclass, field
from pathlib import Path

from casebench.cloud.bundle import (
    MERGED,
    SUITE_FILES,
    Refused,
    merged,
    run_files,
    safe_id,
    suite_files,
)
from casebench.cloud.client import Cloud
from casebench.runs.log import RunLog
from casebench.suites.freeze import load
from casebench.workbench.sources import Workspace


@dataclass
class Pushed:
    runs: list[str] = field(default_factory=list)
    suites: list[str] = field(default_factory=list)
    unchanged: int = 0
    missing_suites: list[str] = field(default_factory=list)


@dataclass
class Pulled:
    suites: list[str] = field(default_factory=list)
    reviews: int = 0
    preferences: int = 0


def push(cloud: Cloud, workspace: Workspace, runs: list[RunLog], traces: bool) -> Pushed:
    """Each run's suite goes first, so the server can show the run beside its cases."""
    out = Pushed()
    suites = workspace.suites()
    for suite_id in sorted({log.info.suite_id for log in runs}):
        suite = suites.get(suite_id)
        if suite is None:
            out.missing_suites.append(suite_id)
            continue
        answer = cloud.push_suite(safe_id(suite_id), suite_files(suite.folder))
        if answer.get("changed"):
            out.suites.append(suite_id)
        else:
            out.unchanged += 1
    for log in runs:
        run_id = safe_id(log.info.run_id)
        answer = cloud.push_run(run_id, run_files(log, traces))
        if answer.get("changed"):
            out.runs.append(run_id)
        else:
            out.unchanged += 1
    return out


def pull(cloud: Cloud, workspace: Workspace) -> Pulled:
    """Suites lawyers changed are written over this machine's copies; reviews and preferences
    are merged into each run's own. No score changes: the next run or gate computes."""
    suites = workspace.suites()
    runs = {log.info.run_id: log for log in workspace.runs()}
    state = cloud.state(sorted(suites), sorted(runs))
    out = Pulled()
    for suite_id, files in (state.get("suites") or {}).items():
        local = suites.get(suite_id)
        if local is None or files["content_hash"] == local.manifest.content_hash:
            continue
        _write_suite(local.folder, files["files"])
        out.suites.append(suite_id)
    for run_id, files in (state.get("runs") or {}).items():
        log = runs.get(run_id)
        if log is None:
            continue
        for name in MERGED:
            theirs = files.get(name) or ""
            path = log.folder / name
            ours = path.read_text(encoding="utf-8") if path.is_file() else ""
            combined = merged(ours, theirs)
            added = len(combined.splitlines()) - len(merged(ours, "").splitlines())
            if added:
                path.write_text(combined, encoding="utf-8")
                if name.startswith("reviews"):
                    out.reviews += added
                else:
                    out.preferences += added
    return out


def _write_suite(folder: Path, files: dict[str, str]) -> None:
    """Written, then read back: a suite whose cases do not match its hash is not kept."""
    if not set(files) <= set(SUITE_FILES):
        raise Refused(f"a suite holds only {', '.join(SUITE_FILES)}")
    before = {name: (folder / name).read_text(encoding="utf-8") for name in files}
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    try:
        load(folder)
    except Exception:
        for name, text in before.items():
            (folder / name).write_text(text, encoding="utf-8")
        raise
