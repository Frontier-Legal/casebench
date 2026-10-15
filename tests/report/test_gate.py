"""A gate in CI: a run fails the build only when it falls significantly below a saved baseline,
over approved cases (decision 0048)."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.core.case import Approval, Case
from casebench.metrics.builtin.outcome import WRONG
from casebench.report.gate import MARKER
from casebench.runs.log import RunLog
from tests.judge.fake_judge import start_fake_judge
from tests.report.suites import criteria_case, frozen, mixed, outcome_case

AGENTS = Path(__file__).parent / "agents.py"
ACTION = Path(__file__).parents[2] / "action.yml"
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def approved(cases: list[Case]) -> list[Case]:
    return [case.model_copy(update={"approval": Approval.APPROVED}) for case in cases]


def suite(project: Path, cases: list[Case]) -> Path:
    """Twelve outcome cases; in one, a late appeal reversed the ruling, which only the
    careful agent gets wrong."""
    return frozen(cases, project / "suite")


def twelve() -> list[Case]:
    cases = mixed(12)
    cases[1] = outcome_case(1, "reversed", "A late appeal court found an error.")
    return cases


def run(project: Path, agent: str, run_id: str, config: str = "none.yaml"):
    return CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(project / "suite"),
            "--config",
            str(project / config),
            "--python",
            f"{AGENTS}:{agent}",
            "--runs-dir",
            str(project / "runs"),
            "--run-id",
            run_id,
            "--commit",
            COMMIT,
        ],
    )


def gate(project: Path, *args: str):
    runs = project / "runs"
    return CliRunner().invoke(main, ["gate", str(runs / "baseline"), str(runs / "new"), *args])


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_suite_as_a_pytest_test(project: Path):
    suite(project, approved(twelve()))
    assert run(project, "from_facts", "baseline").exit_code == 0
    target = {"type": "python", "entry": f"{AGENTS}:from_facts"}
    (project / "casebench.yaml").write_text(yaml.safe_dump({"target": target}), encoding="utf-8")
    (project / "test_legal.py").write_text(
        "import pytest\n\n\n"
        '@pytest.mark.casebench(suite="suite", baseline="runs/baseline", runs_dir="runs")\n'
        "def test_legal_accuracy():\n"
        "    pass\n",
        encoding="utf-8",
    )

    def pytest_run() -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "GITHUB_SHA": COMMIT}
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_legal.py"],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )

    held = pytest_run()
    target["entry"] = f"{AGENTS}:upheld"
    (project / "casebench.yaml").write_text(yaml.safe_dump({"target": target}), encoding="utf-8")
    dropped = pytest_run()

    assert held.returncode == 0, held.stdout + held.stderr
    [first, *_] = sorted((project / "runs").glob("pytest-*"))
    assert json.loads((first / "run.json").read_text())["commit"] == COMMIT
    assert dropped.returncode == 1, dropped.stdout
    assert "Casebench gate failed (exit 1)" in dropped.stdout


def test_significant_drop_fails_the_build(project: Path):
    suite(project, approved(twelve()))
    run(project, "from_facts", "baseline")
    run(project, "upheld", "new")

    dropped = gate(project)
    (project / "runs" / "new").rename(project / "runs" / "worse")
    run(project, "careful", "new")
    slipped = gate(project)

    assert dropped.exit_code == 1, dropped.output
    assert re.search(
        r"outcome · outcome: 100% -> \d+% over 12 cases.*worse, significant", dropped.output
    )
    assert f"  {WRONG}: 0 -> 8" in dropped.output
    assert "gate: failed" in dropped.output
    # One case worse: inside the interval, reported, and the build passes.
    assert slipped.exit_code == 0, slipped.output
    assert "outcome · outcome: 100% -> 92% over 12 cases" in slipped.output
    assert "not significant" in slipped.output and f"  {WRONG}: 0 -> 1" in slipped.output


def test_pull_request_comment(project: Path):
    suite(project, approved(twelve()))
    run(project, "from_facts", "baseline")
    run(project, "upheld", "new")

    gated = gate(project, "--markdown", str(project / "comment.md"))

    assert gated.exit_code == 1
    comment = (project / "comment.md").read_text(encoding="utf-8")
    assert comment.startswith(MARKER)
    assert "| Task · metric | Before | After | Cases | Difference | Change |" in comment
    assert re.search(
        r"\| outcome · outcome \| 100% \| 33% \| 12 "
        r"\| [-+]\d+% to [-+]\d+% \| worse, significant \|",
        comment,
    )
    assert f"- outcome: {WRONG}, 0 -> 8" in comment
    assert "**Gate failed.**" in comment
    # The action runs the gate with --markdown, and posts or updates the comment it marks.
    action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "composite"
    steps = action["runs"]["steps"]
    for step in steps:
        if "uses" in step:
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", step["uses"]), step["uses"]
    scripts = "\n".join(step.get("run", "") for step in steps)
    assert "gate" in scripts and "--markdown" in scripts and MARKER in scripts


def test_approved_cases_only(project: Path):
    cases = twelve()
    suite(project, approved(cases[:9]) + cases[9:])
    run(project, "from_facts", "baseline")
    run(project, "upheld", "new")

    gated = gate(project)

    assert "over 9 cases" in gated.output
    assert "3 draft cases were left out; a lawyer has not approved them" in gated.output


def test_a_gate_before_approvals_exist(project: Path):
    suite(project, twelve())
    run(project, "from_facts", "baseline")
    run(project, "upheld", "new")

    without = gate(project)
    unreviewed = gate(project, "--include-unreviewed")

    assert without.exit_code == 0, without.output
    assert "0 approved cases: nothing to gate yet" in without.output
    assert "gate: passed" in without.output
    assert unreviewed.output.splitlines()[0] == (
        "gating approved and unreviewed cases (--include-unreviewed)"
    )
    assert "over 12 cases" in unreviewed.output
    assert unreviewed.exit_code == 1
    assert RunLog(project / "runs" / "new").info.commit == COMMIT


def test_a_lawyers_verdict_counts_in_the_gate(project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_fake_judge()
    judge = {
        "provider": "anthropic",
        "model": "judge-model",
        "options": {"base_url": f"http://127.0.0.1:{server.server_port}", "max_tokens": 1024},
    }
    (project / "judged.yaml").write_text(yaml.safe_dump({"judge": judge}), encoding="utf-8")
    suite(project, approved([criteria_case(n, {"Mentions upheld": 1}) for n in range(12)]))
    run(project, "upheld", "baseline", "judged.yaml")
    run(project, "upheld", "new", "judged.yaml")
    server.shutdown()
    held = gate(project)
    for n in range(8):
        CliRunner().invoke(
            main,
            [
                "review", "criterion", str(project / "runs" / "new"), "--case", f"case-{n:03d}",
                "--criterion", "c1", "--verdict", "fail", "--by", "Ayşe",
                "--note", "it names the outcome but not the reason",
            ],
        )  # fmt: skip

    overruled = gate(project)

    assert held.exit_code == 0, held.output
    # The lawyer's verdicts replace the judge's in the run, as in its report, with no new score set.
    assert overruled.exit_code == 1, overruled.output
    assert "qa · criteria: 100% -> 33% over 12 cases" in overruled.output
    assert "  failed outcome criteria: 0 -> 8" in overruled.output
