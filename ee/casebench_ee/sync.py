# SPDX-License-Identifier: Elastic-2.0
"""The team server's sync routes: runs and suites pushed in, lawyers' decisions pulled out.

The server stores what the runner computed and never scores (decision 0059).
"""

import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from casebench.cloud.bundle import (
    MERGED,
    SUITE_FILES,
    Refused,
    merged,
    run_file,
    safe_id,
)
from casebench.runs.log import RESULTS_FILE, RUN_FILE, Result, RunInfo
from casebench.suites.freeze import load
from casebench.workbench.access import Can, refuse
from casebench.workbench.app import Who
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Event, Store

# The hash of the suite as the engineer last pushed it; a different one on the server means
# lawyers changed it here since.
PUSHED = ".pushed-hash"
SYNC_ITEM = "sync"
LARGEST = 64 * 2**20


class Files(BaseModel):
    files: dict[str, str]


class Stored(BaseModel):
    changed: list[str] = Field(default_factory=list)
    content_hash: str | None = None


class StateRequest(BaseModel):
    suites: list[str] = Field(default_factory=list)
    runs: list[str] = Field(default_factory=list)


class SuiteState(BaseModel):
    content_hash: str
    files: dict[str, str]


class State(BaseModel):
    suites: dict[str, SuiteState]
    runs: dict[str, dict[str, str]]


def inside(base: Path, *parts: str) -> Path:
    """A path under `base`, resolved; refused when it would leave it."""
    root = os.path.realpath(base)
    full = os.path.realpath(os.path.join(root, *parts))
    if not full.startswith(root + os.sep):
        raise HTTPException(422, "that path leaves the server's folder")
    return Path(full)


def _too_large(files: dict[str, str]) -> None:
    if sum(len(text) for text in files.values()) > LARGEST:
        raise HTTPException(413, "push fewer runs at a time; this is over 64 MB")


def _lines(text: str, path: str) -> list[dict]:
    try:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except json.JSONDecodeError:
        raise HTTPException(422, f"{path} is not one JSON object per line") from None


def sync_routes(workspace: Workspace, store: Store) -> APIRouter:
    router = APIRouter()

    def where(suite_id: str) -> Path:
        found = workspace.suites().get(suite_id)
        return found.folder if found else inside(workspace.suite_dirs[0], suite_id)

    @router.post("/api/sync/suites/{suite_id}")
    def push_suite(suite_id: str, body: Files, who: Who) -> Stored:
        """Refused when lawyers changed the suite here since the last push: pull first."""
        refuse(who, Can.ENGINEER)
        try:
            safe_id(suite_id)
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None
        if set(body.files) != set(SUITE_FILES):
            raise HTTPException(422, f"a suite is sent as {', '.join(SUITE_FILES)}")
        _too_large(body.files)
        with tempfile.TemporaryDirectory() as scratch:
            for name in SUITE_FILES:
                (Path(scratch) / name).write_text(body.files[name], encoding="utf-8")
            try:
                manifest, _ = load(Path(scratch))
            except Exception as failure:
                raise HTTPException(422, f"the suite does not read back: {failure}") from None
        if manifest.suite_id != suite_id:
            raise HTTPException(422, f"the manifest names suite {manifest.suite_id}")
        folder = where(suite_id)
        current = workspace.suites().get(suite_id)
        marker = folder / PUSHED
        if current is not None:
            if current.manifest.content_hash == manifest.content_hash:
                marker.write_text(manifest.content_hash, encoding="utf-8")
                return Stored(content_hash=manifest.content_hash)
            last = marker.read_text(encoding="utf-8").strip() if marker.is_file() else None
            if last != current.manifest.content_hash:
                raise HTTPException(
                    409,
                    f"suite {suite_id} changed on the server since your last push, where "
                    "lawyers approved or edited cases; run casebench pull, then push again",
                )
        folder.mkdir(parents=True, exist_ok=True)
        for name in SUITE_FILES:
            (folder / name).write_text(body.files[name], encoding="utf-8")
        marker.write_text(manifest.content_hash, encoding="utf-8")
        store.log(
            [
                Event(
                    by=who.name,
                    action="pushed suite",
                    item=SYNC_ITEM,
                    subject=suite_id,
                    before=current.manifest.content_hash if current else None,
                    after=manifest.content_hash,
                )
            ]
        )
        return Stored(changed=sorted(body.files), content_hash=manifest.content_hash)

    @router.post("/api/sync/runs/{run_id}")
    def push_run(run_id: str, body: Files, who: Who) -> Stored:
        """Only a run's sent files; reviews and preferences merged; a score set never rewritten."""
        refuse(who, Can.ENGINEER)
        try:
            safe_id(run_id)
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None
        refused_paths = [p for p in body.files if not run_file(p)]
        if refused_paths:
            raise HTTPException(422, f"these do not cross the line: {', '.join(refused_paths)}")
        _too_large(body.files)
        folder = inside(workspace.runs_dir, run_id)
        if RUN_FILE not in body.files and not (folder / RUN_FILE).is_file():
            raise HTTPException(422, f"a new run is sent with its {RUN_FILE}")
        if RUN_FILE in body.files:
            info = RunInfo.model_validate_json(body.files[RUN_FILE])
            if info.run_id != run_id:
                raise HTTPException(422, f"{RUN_FILE} names run {info.run_id}")
        for path, text in body.files.items():
            if path.endswith(".jsonl"):
                lines = _lines(text, path)
                if path == RESULTS_FILE:
                    for line in lines:
                        Result.model_validate(line)
        changed = []
        for path, text in sorted(body.files.items()):
            target = inside(folder, path)
            old = target.read_text(encoding="utf-8") if target.is_file() else None
            if path in MERGED:
                text = merged(old or "", text)
            elif path.startswith("scores/") and old is not None and old != text:
                raise HTTPException(409, f"score set {path} differs from the one pushed before")
            if text != old:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                changed.append(path)
        if changed:
            store.log(
                [
                    Event(
                        by=who.name,
                        action="pushed run",
                        item=SYNC_ITEM,
                        subject=run_id,
                        after={"files": changed},
                    )
                ]
            )
        return Stored(changed=changed)

    @router.post("/api/sync/state")
    def state(body: StateRequest, who: Who) -> State:
        """What the engineer pulls: the suites and the runs they asked for that are here."""
        refuse(who, Can.ENGINEER)
        suites = workspace.suites()
        out_suites = {}
        for suite_id in body.suites:
            found = suites.get(suite_id)
            if found is None:
                continue
            out_suites[suite_id] = SuiteState(
                content_hash=found.manifest.content_hash,
                files={n: (found.folder / n).read_text(encoding="utf-8") for n in SUITE_FILES},
            )
        out_runs = {}
        for run_id in body.runs:
            log = workspace.run(run_id)
            if log is None:
                continue
            out_runs[run_id] = {
                name: (log.folder / name).read_text(encoding="utf-8")
                for name in MERGED
                if (log.folder / name).is_file()
            }
        return State(suites=out_suites, runs=out_runs)

    return router
