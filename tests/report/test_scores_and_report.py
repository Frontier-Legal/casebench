"""Deterministic scores, honest baselines and intervals."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.metrics.builtin.outcome import WRONG, labels_in
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.suites.freeze import load
from tests.judge.fake_judge import FakeJudge, start_fake_judge
from tests.report.suites import frozen, mixed, outcome_case

AGENTS = Path(__file__).parent / "agents.py"


@pytest.fixture
def judged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A config with a judge whose every call is counted, and a folder corpus."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("CASEBENCH_TEST_CALLS", str(tmp_path / "calls.txt"))
    FakeJudge.calls.clear()
    server = start_fake_judge()
    store = tmp_path / "decisions"
    store.mkdir()
    config = tmp_path / "casebench.yaml"
    options = f"{{base_url: 'http://127.0.0.1:{server.server_port}', max_tokens: 1024}}"
    config.write_text(
        f"judge: {{provider: anthropic, model: judge-model, options: {options}}}\n"
        f"corpus: {{connector: folder, options: {{path: '{store.as_posix()}'}}}}\n",
        encoding="utf-8",
    )
    yield config
    server.shutdown()


def target_calls(tmp_path: Path) -> int:
    calls = tmp_path / "calls.txt"
    return len(calls.read_text(encoding="utf-8").splitlines()) if calls.is_file() else 0


def run(suite: Path, runs: Path, agent: str, *extra: str):
    return CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(suite),
            "--python",
            f"{AGENTS}:{agent}",
            "--runs-dir",
            str(runs),
            "--no-capture",
            *extra,
        ],
    )


def test_wrong_outcome(tmp_path: Path, judged: Path):
    suite = frozen(
        [outcome_case(1, "reversed", "The appeal court found an error.")], tmp_path / "s"
    )

    ran = run(suite, tmp_path / "runs", "upheld", "--config", str(judged), "--run-id", "r")

    assert ran.exit_code == 0, ran.output
    [score] = json.loads((tmp_path / "runs" / "r" / "report.json").read_text("utf-8"))["scores"]
    assert (score["value"], score["label"]) == (0.0, WRONG)
    assert FakeJudge.calls == []
    assert labels_in("Partly reversed, not reversed in full.") == {"partly_reversed", "reversed"}
    assert labels_in("It was partly reversed.") == {"partly_reversed"}
    assert labels_in("I cannot tell.") == set()


def test_baselines_shown(tmp_path: Path):
    suite = frozen(mixed(9), tmp_path / "suite")

    ran = run(suite, tmp_path / "runs", "upheld", "--run-id", "r")

    assert ran.exit_code == 0, ran.output
    lines = ran.output.splitlines()
    header = next(i for i, line in enumerate(lines) if "majority" in line)
    score, _, majority, text_only = lines[header + 1].split()[-4:]
    assert (score, majority, text_only) == ("33%", "67%", "100%")
    [table] = json.loads((tmp_path / "runs" / "r" / "report.json").read_text("utf-8"))["tables"]
    [row_json] = table["rows"]
    assert row_json["majority_baseline"] == pytest.approx(6 / 9)
    assert row_json["text_only_baseline"] == 1.0  # the facts give the ruling away


def test_noise_marked(tmp_path: Path):
    late = outcome_case(99, "upheld", "The appeal was late.")
    suite = frozen([*mixed(30), late], tmp_path / "suite")
    runs = tmp_path / "runs"
    for name, agent in (("a", "from_facts"), ("b", "careful"), ("c", "upheld")):
        assert run(suite, runs, agent, "--run-id", name).exit_code == 0

    one_case = CliRunner().invoke(main, ["compare", str(runs / "a"), str(runs / "b")])
    every_case = CliRunner().invoke(main, ["compare", str(runs / "a"), str(runs / "c")])

    assert one_case.exit_code == 0, one_case.output
    assert "97% -> 100% over 31 cases" in one_case.output
    assert one_case.output.rstrip().endswith(", not significant")
    assert every_case.output.rstrip().endswith(", significant")


def test_dry_run(tmp_path: Path, judged: Path):
    cases = [
        outcome_case(n, "reversed", "The appeal court found an error.", ["citation_integrity"])
        for n in range(500)
    ]
    suite = frozen(cases, tmp_path / "suite")

    ran = run(suite, tmp_path / "runs", "upheld", "--config", str(judged), "--dry-run")

    assert ran.exit_code == 0, ran.output
    characters = sum(len(str(v)) for c in cases for v in c.task.inputs.values())
    assert f"target: 500 calls (0 cases already stored), about {characters // 4} input tokens" in (
        ran.output
    )
    assert "judge: at least 500 calls and" in ran.output
    assert "corpus: one search per citation and up to 5 document fetches each; 0 documents" in (
        ran.output
    )
    assert "nothing was sent" in ran.output
    assert (target_calls(tmp_path), FakeJudge.calls) == (0, [])
    assert not (tmp_path / "runs").exists()


def test_rerun_after_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CASEBENCH_TEST_CALLS", str(tmp_path / "calls.txt"))
    suite = frozen(mixed(500), tmp_path / "suite")
    manifest, cases = load(suite)
    info = RunInfo(
        run_id="r", suite_id=manifest.suite_id, suite_hash=manifest.content_hash, target="python"
    )
    log = RunLog.create(tmp_path / "runs" / "r", info)
    for case in cases[:312]:
        log.append(Result(case_id=case.id, output="Stored before the crash: reversed."))

    ran = run(suite, tmp_path / "runs", "upheld", "--run-id", "r")

    assert ran.exit_code == 0, ran.output
    assert "188 cases sent, 500 stored" in ran.output
    assert target_calls(tmp_path) == 188
    stored = {r.case_id: r.output for r in log.results()}
    assert all(stored[c.id] == "Stored before the crash: reversed." for c in cases[:312])


def test_terminal_and_json_report(tmp_path: Path):
    suite = frozen(mixed(9), tmp_path / "suite")

    ran = run(suite, tmp_path / "runs", "upheld", "--run-id", "r")

    assert ran.exit_code == 0, ran.output
    folder = tmp_path / "runs" / "r"
    assert (folder / "results.jsonl").is_file()
    report = json.loads((folder / "report.json").read_text("utf-8"))
    [table] = report["tables"]
    assert (table["task_type"], table["metric"]) == ("outcome", "outcome")
    [row] = table["rows"]
    assert row["n"] == 9
    assert row["mean"] == pytest.approx(3 / 9)
    assert row["low"] <= row["mean"] <= row["high"]
    assert "outcome · outcome" in ran.output
    assert "n" in ran.output.split() and "95% interval" in ran.output
    assert f"{row['low']:.0%}-{row['high']:.0%}" in ran.output
    labels = sorted(s["label"] for s in report["scores"])
    assert labels == ["correct"] * 3 + [WRONG] * 6

    again = CliRunner().invoke(main, ["report", str(folder)])

    assert again.exit_code == 0, again.output
    assert again.output in ran.output
