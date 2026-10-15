"""A run's folder: what ran, every result as it finished, and every score set."""

import json
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import Field

from casebench import __version__, keys
from casebench.capture.step import Step
from casebench.core.model import FrozenRecord
from casebench.core.score import Score
from casebench.runs.producer import Producer

RUN_FILE = "run.json"
RESULTS_FILE = "results.jsonl"
SCORES_DIR = "scores"
PRODUCER = "produced_by"
SCORING_ERROR = "scoring_error"


class RunInfo(FrozenRecord):
    """What a run ran: which suite, against which target, with which Casebench."""

    run_id: str
    suite_id: str
    suite_hash: str
    target: str
    # Read when a record is made, so the version is no default in the format's schema, which
    # would change with every release.
    casebench_version: str = Field(default_factory=lambda: __version__)
    commit: str | None = Field(default=None, description="The code's commit (decision 0048).")


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


class ScoringError(FrozenRecord):
    """A metric that could not score one result, such as a judge call that still failed after
    its retries; the case has no score for it until the run is scored again (decision 0037)."""

    case_id: str
    repeat: int = 0
    metric: str
    error: str


class RunLog:
    """Append-only access to one run's folder. Every line is scrubbed of keys before it is
    written (decision 0046)."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    @classmethod
    def create(cls, folder: Path, info: RunInfo) -> "RunLog":
        folder.mkdir(parents=True, exist_ok=False)
        written = keys.scrub(info.model_dump_json(indent=2))
        (folder / RUN_FILE).write_text(written + "\n", encoding="utf-8")
        return cls(folder)

    @property
    def info(self) -> RunInfo:
        return RunInfo.model_validate_json((self.folder / RUN_FILE).read_text(encoding="utf-8"))

    def append(self, result: Result) -> None:
        """Persist one result before the next case starts."""
        with (self.folder / RESULTS_FILE).open("a", encoding="utf-8") as stream:
            stream.write(keys.scrub(result.model_dump_json()) + "\n")

    def results(self) -> list[Result]:
        path = self.folder / RESULTS_FILE
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [Result.model_validate_json(line) for line in lines if line]

    def write_score_set(
        self,
        scores: Iterable[Score],
        producer: Producer,
        errors: Iterable[ScoringError] = (),
    ) -> Path:
        """Write a new score set beside the existing ones; never rewrite an old one. Its first
        line says what produced it (decision 0035); each error has a line of its own."""
        directory = self.folder / SCORES_DIR
        directory.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = directory / f"{stamp}-{uuid.uuid4().hex}.jsonl"
        with path.open("x", encoding="utf-8") as stream:
            lines = [json.dumps({PRODUCER: producer.model_dump(mode="json")})]
            lines += [score.model_dump_json() for score in scores]
            lines += [json.dumps({SCORING_ERROR: e.model_dump(mode="json")}) for e in errors]
            for line in lines:
                stream.write(keys.scrub(line) + "\n")
        return path

    def score_sets(self) -> list[Path]:
        directory = self.folder / SCORES_DIR
        return sorted(directory.glob("*.jsonl")) if directory.exists() else []

    @staticmethod
    def _lines(path: Path) -> list[dict]:
        """Every line but the header; a set written before headers has none (decision 0042)."""
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        return [line for line in lines if PRODUCER not in line]

    @staticmethod
    def read_scores(path: Path) -> list[Score]:
        lines = RunLog._lines(path)
        return [Score.model_validate(line) for line in lines if SCORING_ERROR not in line]

    @staticmethod
    def read_errors(path: Path) -> list[ScoringError]:
        lines = RunLog._lines(path)
        return [
            ScoringError.model_validate(line[SCORING_ERROR])
            for line in lines
            if SCORING_ERROR in line
        ]

    @staticmethod
    def read_producer(path: Path) -> Producer | None:
        """None for a set written before score sets said what produced them."""
        with path.open(encoding="utf-8") as stream:
            first = json.loads(stream.readline() or "{}")
        return Producer.model_validate(first[PRODUCER]) if PRODUCER in first else None
