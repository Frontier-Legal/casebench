"""A run's folder: what ran, every result as it finished, and every score set."""

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field

from casebench import __version__
from casebench.capture.step import Step
from casebench.core.model import FrozenRecord
from casebench.core.score import Score

RUN_FILE = "run.json"
RESULTS_FILE = "results.jsonl"
SCORES_DIR = "scores"


class RunInfo(FrozenRecord):
    """What a run ran: which suite, against which target, with which Casebench."""

    run_id: str
    suite_id: str
    suite_hash: str
    target: str
    casebench_version: str = __version__


class Result(FrozenRecord):
    """The target's output for one case and repeat."""

    case_id: str
    repeat: int = 0
    output: str | None = None
    citations: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    error: str | None = None
    latency_ms: float | None = None


class RunLog:
    """Append-only access to one run's folder."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    @classmethod
    def create(cls, folder: Path, info: RunInfo) -> "RunLog":
        folder.mkdir(parents=True, exist_ok=False)
        (folder / RUN_FILE).write_text(info.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return cls(folder)

    @property
    def info(self) -> RunInfo:
        return RunInfo.model_validate_json((self.folder / RUN_FILE).read_text(encoding="utf-8"))

    def append(self, result: Result) -> None:
        """Persist one result before the next case starts."""
        with (self.folder / RESULTS_FILE).open("a", encoding="utf-8") as stream:
            stream.write(result.model_dump_json() + "\n")

    def results(self) -> list[Result]:
        path = self.folder / RESULTS_FILE
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [Result.model_validate_json(line) for line in lines if line]

    def write_score_set(self, scores: Iterable[Score]) -> Path:
        """Write a new score set beside the existing ones; never rewrite an old one."""
        directory = self.folder / SCORES_DIR
        directory.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = directory / f"{stamp}-{uuid.uuid4().hex}.jsonl"
        with path.open("x", encoding="utf-8") as stream:
            for score in scores:
                stream.write(score.model_dump_json() + "\n")
        return path

    def score_sets(self) -> list[Path]:
        directory = self.folder / SCORES_DIR
        return sorted(directory.glob("*.jsonl")) if directory.exists() else []

    @staticmethod
    def read_scores(path: Path) -> list[Score]:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [Score.model_validate_json(line) for line in lines if line]
