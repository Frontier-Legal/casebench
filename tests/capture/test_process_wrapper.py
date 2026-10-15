"""Every model call, tool call and backend step captured with no change to the agent's code:
the Python process wrapper."""

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.capture.step import StepKind
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import RunLog
from casebench.suites.freeze import freeze
from tests.capture.openai_upstream import start_openai

AGENT = Path(__file__).resolve().parent / "sdk_agent.py"


def suite(folder: Path, count: int) -> Path:
    cases = [
        Case(
            id=f"c{n}",
            task=Task.model_validate({"type": "qa", "question": f"Q{n}?"}),
            reference=Reference(source=ReferenceSource.LAWYER),
            metrics=[],
        )
        for n in range(count)
    ]
    freeze("wrapper", cases, folder)
    return folder


def run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, cases: int, concurrency: int) -> RunLog:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    upstream = start_openai()
    agent = tmp_path / "agent.py"  # a fresh path is a fresh import, so a fresh client
    shutil.copy(AGENT, agent)
    config = tmp_path / "casebench.yaml"
    config.write_text(
        "target: {type: python, entry: unused:unused}\n"
        f"capture:\n  routes:\n    - {{name: openai, upstream: 'http://127.0.0.1:{upstream.server_port}'}}\n",
        encoding="utf-8",
    )
    try:
        result = CliRunner().invoke(
            main,
            [
                "run",
                "--suite",
                str(suite(tmp_path / "suite", cases)),
                "--config",
                str(config),
                "--python",
                str(agent),
                "--max-concurrency",
                str(concurrency),
                "--runs-dir",
                str(tmp_path / "runs"),
                "--run-id",
                "r1",
            ],
        )
    finally:
        upstream.shutdown()
    assert result.exit_code == 0, result.output
    assert f"{cases} cases sent" in result.output
    return RunLog(tmp_path / "runs" / "r1")


def test_process_wrapper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    [result] = run(tmp_path, monkeypatch, cases=1, concurrency=1).results()

    assert result.error is None and result.output == "Short: invalid."
    calls = [s for s in result.steps if s.kind is StepKind.LLM]
    assert [(s.provider, s.model, s.input_tokens, s.output_tokens) for s in calls] == [
        ("openai", "gpt-5", 90, 12),
        ("openai", "gpt-5", 150, 8),
        ("openai", "gpt-5", 30, 4),
    ]
    assert all(s.duration_ms and s.duration_ms > 0 for s in calls)
    [tool] = [s for s in result.steps if s.kind is StepKind.TOOL]
    # The arguments are dropped before the result is stored (decision 0062).
    assert (tool.name, tool.arguments, tool.result_size) == ("search", None, 10)
    assert tool.duration_ms is not None
    [gap] = [s for s in result.steps if s.kind is StepKind.GAP]
    assert gap.name == "between llm gpt-5 and llm gpt-5"
    assert gap.duration_ms is not None and gap.duration_ms > 0


def test_concurrent_python_cases_keep_their_own_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    results = run(tmp_path, monkeypatch, cases=4, concurrency=4).results()

    assert len(results) == 4
    for result in results:
        assert len([s for s in result.steps if s.kind is StepKind.LLM]) == 3
        assert len([s for s in result.steps if s.kind is StepKind.TOOL]) == 1
