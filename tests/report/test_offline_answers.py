"""Answers from a tool Casebench cannot reach, scored as a connected run's are (decision 0061)."""

import csv
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.runs.log import RunLog
from tests.report import agents
from tests.report.suites import frozen, mixed

AGENTS = Path(__file__).parent / "agents.py"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    frozen(mixed(9), tmp_path / "suite")
    return tmp_path


def values(run_dir: Path) -> dict[tuple[str, str], float]:
    log = RunLog(run_dir)
    return {(s.case_id, s.metric): s.value for s in RunLog.read_scores(log.score_sets()[-1])}


def test_offline_answers_for_a_closed_tool(project: Path):
    connected = CliRunner().invoke(
        main,
        ["run", "--suite", "suite", "--config", "none.yaml", "--python",
         f"{AGENTS}:from_facts", "--runs-dir", "runs", "--run-id", "connected"],
    )  # fmt: skip
    exported = CliRunner().invoke(
        main, ["export", "--format", "csv", "--suite", "suite", "--out", "questions.csv"]
    )
    # Someone pastes each question into the closed tool and writes its answer down.
    with (project / "questions.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows[:-1]:
        row["answer"] = agents.from_facts(row["question"], row["facts"])
    with (project / "answers.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    imported = CliRunner().invoke(
        main, ["import", "answers.csv", "--suite", "suite", "--runs-dir", "runs"]
    )
    [offline] = [p for p in (project / "runs").iterdir() if p.name != "connected"]

    assert connected.exit_code == 0, connected.output
    assert exported.exit_code == 0, exported.output
    assert list(rows[0]) == ["case_id", "repeat", "facts", "question", "answer"]
    assert imported.exit_code == 0, imported.output
    assert "8 answers from answers.csv, 1 cases unanswered" in imported.output
    assert RunLog(offline).info.target == "offline"
    on_line = values(project / "runs" / "connected")
    off_line = values(offline)
    assert off_line and all(on_line[key] == value for key, value in off_line.items())
    assert len(off_line) == 8


def test_a_bad_answer_row_is_named(project: Path):
    (project / "answers.csv").write_text(
        "case_id,repeat,answer\nno-such-case,0,Upheld.\n", encoding="utf-8"
    )

    imported = CliRunner().invoke(main, ["import", "answers.csv", "--suite", "suite"])

    assert imported.exit_code != 0
    assert "answers.csv, row 2: the suite has no case 'no-such-case'" in imported.output
