"""The workbench finds a project's suites without walking its dependencies (decision 0050)."""

from pathlib import Path

from casebench.suites.freeze import freeze
from casebench.workbench.sources import Workspace
from tests.workbench.test_review_queue import reviewed_case


def test_suites_are_found_without_walking_dependencies(tmp_path: Path):
    case = reviewed_case()
    freeze("mine", [case], tmp_path / ".casebench" / "suites" / "mine")
    freeze("evals", [case], tmp_path / "evals" / "labour")
    for hidden in ("node_modules/pkg", ".venv/lib", ".claude/worktrees/copy", "env/lib"):
        freeze("dependency", [case], tmp_path / hidden / "suite")
    (tmp_path / "env" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")

    found = Workspace(tmp_path / ".casebench" / "runs", [tmp_path]).suites()

    assert sorted(found) == ["evals", "mine"]
