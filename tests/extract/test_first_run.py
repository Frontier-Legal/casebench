"""The first `casebench run` builds its own suite after a cost confirmation (decision 0061)."""

from pathlib import Path

from casebench.runs.first import FIRST
from casebench.runs.log import RESULTS_FILE, RunLog
from tests.extract.fake_models import FakeModels
from tests.extract.test_answer_keys import invoke, workspace  # noqa: F401

AGENT = "def answer(question):\n    return 'Reversed.'\n"


def test_first_run_does_the_rest(workspace):  # noqa: F811
    tmp_path, config, _ = workspace
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    config.write_text(
        "target: {type: python, entry: agent.py}\n" + config.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    FakeModels.bodies.clear()
    arguments = ("run", "--sample", "6", "--cases", "3", "--no-capture")

    unconfirmed = invoke(*arguments)
    asked_before = len(FakeModels.bodies)
    kept_before = (tmp_path / ".casebench" / "keys").exists()
    first = invoke(*arguments, "--yes")
    [run_dir] = list((tmp_path / ".casebench" / "runs").iterdir())
    # The run stops after its first answer, as an interrupted one does.
    results = run_dir / RESULTS_FILE
    results.write_text(results.read_text("utf-8").splitlines()[0] + "\n", encoding="utf-8")
    extracted = len(FakeModels.bodies)
    resumed = invoke(*arguments)

    # It shows the cost and waits: with no answer, nothing is spent.
    assert unconfirmed.exit_code != 0
    assert "extract: 6 decisions, 12 model calls" in unconfirmed.output
    assert "pass --yes" in unconfirmed.output
    assert asked_before == 0 and not kept_before
    # Confirmed, it extracts, generates and runs, and says where to open the run.
    assert first.exit_code == 0, first.output
    assert "6 decisions read, 5 answer keys kept" in first.output
    assert "suite first: 3 cases" in first.output
    assert (tmp_path / FIRST / "manifest.json").is_file()
    assert "open it in the workbench: casebench ui" in first.output
    # A second run extracts nothing again and resumes the run that stopped.
    assert resumed.exit_code == 0, resumed.output
    assert f"resuming run {run_dir.name}" in resumed.output
    assert len(FakeModels.bodies) == extracted
    assert len(RunLog(run_dir).results()) == 3
    assert list((tmp_path / ".casebench" / "runs").iterdir()) == [run_dir]


def test_a_run_needs_a_suite_or_the_means_to_build_one(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "casebench.yaml").write_text(
        "target: {type: python, entry: agent.py}\n", encoding="utf-8"
    )

    ran = invoke("run", "--yes")

    assert ran.exit_code != 0
    assert "needs `corpus:` and `extract:`" in ran.output
