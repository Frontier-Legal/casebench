"""A run the workbench started: `casebench run` in a child process, with what it prints so far.

The child is the same command a terminal runs, so it captures, resumes and scores the same
way; one runs at a time (decision 0063).
"""

import os
import re
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from casebench import keys

State = Literal["running", "finished", "failed", "stopped"]
# The lines `casebench run` prints to a log as each case is answered and scored (0038).
ANSWERED = re.compile(r"^(?:answered|failed) (\d+)/(\d+) ")
SCORED = re.compile(r"^scored (\d+)/(\d+) ")
STARTED = re.compile(r"^run (\S+): \d+ cases sent")
UNSCORED = re.compile(r"^scoring errors: (\d+) results? ha(?:ve|s) no score")
RESUMING = re.compile(r"^resuming run (\S+),")


class Busy(RuntimeError):
    """A run is already going; the message names it."""


class JobView(BaseModel):
    id: str
    title: str
    suite_id: str | None = Field(description="The suite it runs; None while the first is built.")
    state: State
    started_at: str
    finished_at: str | None = None
    exit_code: int | None = None
    run_id: str | None = None
    answered: int = 0
    scored: int = 0
    total: int | None = None
    unscored: int = Field(default=0, description="Results the judge could not score this time.")
    line_count: int = 0
    lines: list[str] = Field(
        default_factory=list, description="What it printed, from the line the page asked for."
    )


class Job:
    def __init__(self, title: str, argv: list[str], cwd: Path, suite_id: str | None) -> None:
        self.view = JobView(
            id=uuid.uuid4().hex,
            title=title,
            suite_id=suite_id,
            state="running",
            started_at=datetime.now(UTC).isoformat(),
        )
        self.lock = threading.Lock()
        environment = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
        self.process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.stopping = False
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        for raw in self.process.stdout:
            self._take(keys.scrub(raw.rstrip("\n")))
        code = self.process.wait()
        with self.lock:
            self.view.exit_code = code
            self.view.finished_at = datetime.now(UTC).isoformat()
            if self.stopping:
                self.view.state = "stopped"
            else:
                self.view.state = "finished" if code == 0 else "failed"

    def _take(self, line: str) -> None:
        with self.lock:
            view = self.view
            view.lines.append(line)
            view.line_count += 1
            if found := ANSWERED.match(line):
                view.answered, view.total = int(found[1]), int(found[2])
            elif found := SCORED.match(line):
                view.scored, view.total = int(found[1]), int(found[2])
            elif found := STARTED.match(line) or RESUMING.match(line):
                view.run_id = found[1]
            elif found := UNSCORED.match(line):
                view.unscored = int(found[1])

    def snapshot(self, since: int = 0) -> JobView:
        """Its state, with the lines printed from `since` on, so a page polling it is sent
        only what is new."""
        with self.lock:
            return self.view.model_copy(update={"lines": self.view.lines[since:]})

    def stop(self) -> None:
        """Each answer is stored as it comes, so a stopped run resumes where it stopped."""
        self.stopping = True
        self.process.terminate()


class Jobs:
    """The workbench's runs, the latest first; at most one is going."""

    def __init__(self) -> None:
        self.started: list[Job] = []
        self.lock = threading.Lock()

    def current(self) -> Job | None:
        return self.started[0] if self.started else None

    def start(self, title: str, argv: list[str], cwd: Path, suite_id: str | None) -> Job:
        with self.lock:
            going = self.current()
            if going is not None and going.snapshot().state == "running":
                raise Busy(f"the run of {going.view.title} is still going; stop it or wait")
            job = Job(title, argv, cwd, suite_id)
            self.started.insert(0, job)
            return job

    def find(self, job_id: str) -> Job | None:
        return next((job for job in self.started if job.view.id == job_id), None)
