"""The runs and suites the workbench reads, as they are on disk (decision 0050)."""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path

from casebench.core.case import Case
from casebench.corpus.corpora import Corpora
from casebench.corpus.record import DecisionRecord
from casebench.formats.version import UnreadableFormat
from casebench.judge.families import AgentModel
from casebench.runs.log import RUN_FILE, RunLog
from casebench.suites.freeze import MANIFEST_FILE, SuiteManifest, load

# Folders no suite lives in, never entered when looking for suites: walking a project's
# dependencies took 21 s in a 8.6 GB repository (measured 2026-10-21).
SKIPPED = {"node_modules", ".git", ".venv", "__pycache__", "site-packages"}
# The one hidden folder suites live in, as `casebench run` writes them.
OWN = ".casebench"


@dataclass(frozen=True)
class SuiteFolder:
    folder: Path
    manifest: SuiteManifest
    cases: list[Case]

    def case(self, case_id: str) -> Case | None:
        return next((case for case in self.cases if case.id == case_id), None)


class Workspace:
    """`suite_dirs` are searched for frozen suites; a run finds its suite by the suite's id."""

    def __init__(
        self,
        runs_dir: Path,
        suite_dirs: list[Path],
        corpora: Corpora | None = None,
        agent_models: list[AgentModel] | None = None,
    ) -> None:
        self.runs_dir = runs_dir
        self.suite_dirs = suite_dirs
        self.corpora = corpora
        # Their prices say what each answer cost the agent (decision 0051).
        self.agent_models = agent_models or []

    def _manifests(self) -> list[Path]:
        """Every suite's manifest, never descending into dependencies, virtual environments,
        hidden folders other than Casebench's own, or the runs."""
        found: list[Path] = []
        runs = self.runs_dir.resolve()
        for root in self.suite_dirs:
            for folder, dirs, files in os.walk(root):
                here = Path(folder)
                dirs[:] = sorted(
                    d
                    for d in dirs
                    if d not in SKIPPED
                    and (not d.startswith(".") or d == OWN)
                    and not (here / d / "pyvenv.cfg").is_file()
                    and not (here / d).resolve().is_relative_to(runs)
                )
                if MANIFEST_FILE in files:
                    found.append(here / MANIFEST_FILE)
        return found

    def suites(self) -> dict[str, SuiteFolder]:
        out: dict[str, SuiteFolder] = {}
        for path in self._manifests():
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    manifest, cases = load(path.parent)
            except (UnreadableFormat, ValueError, OSError):
                continue
            out.setdefault(manifest.suite_id, SuiteFolder(path.parent, manifest, cases))
        return out

    def runs(self) -> list[RunLog]:
        if not self.runs_dir.is_dir():
            return []
        folders = [f for f in self.runs_dir.iterdir() if (f / RUN_FILE).is_file()]
        return [RunLog(folder) for folder in sorted(folders)]

    def run(self, run_id: str) -> RunLog | None:
        folder = self.runs_dir / run_id
        if folder.parent != self.runs_dir or not (folder / RUN_FILE).is_file():
            return None
        return RunLog(folder)

    def decision(self, document_id: str) -> DecisionRecord | None:
        """A corpus document, when a corpus is configured and holds it."""
        if self.corpora is None:
            return None
        try:
            return self.corpora.decision(document_id)
        except Exception:
            return None
