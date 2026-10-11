"""A case reaches any agent: Python entry point, HTTP endpoint or command."""

import asyncio
import socket
import sys
import threading
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.capture.step import StepKind
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import RunInfo, RunLog
from casebench.runs.runner import run_cases
from casebench.targets.builtin.http import Target as HttpTarget
from casebench.targets.load import target_from_config
from tests.targets.server import serve

HERE = Path(__file__).resolve().parent


def case(case_id: str, **inputs: str) -> Case:
    return Case(
        id=case_id,
        task=Task.model_validate({"type": "qa", **inputs}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )


def new_log(tmp_path: Path) -> RunLog:
    info = RunInfo(run_id="r", suite_id="s", suite_hash="sha256:x", target="t")
    return RunLog.create(tmp_path / "run", info)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_python_entry_point(tmp_path: Path):
    log = new_log(tmp_path)
    the_case = case("c1", question="Is it valid?", facts="Dismissed by text.", document="x")

    target = target_from_config({"type": "python", "entry": "tests.targets.agents:answer"})
    [result] = asyncio.run(run_cases([the_case], target, log))

    assert result.output == "Asked: Is it valid? Given: Dismissed by text."
    assert result.citations == ["E2023/1-K2024/2"]
    assert result.documents == ["tr-1"]
    assert [step.name for step in result.steps] == ["search"]

    plain = target_from_config({"type": "python", "entry": "tests.targets.agents:plain"})
    [text_only] = asyncio.run(
        run_cases([case("c2", question="Q?")], plain, new_log(tmp_path / "2"))
    )
    # A plain-text answer keeps its text; the judge lists its citations when it grades.
    assert (text_only.output or "").startswith("The court relied on")
    assert text_only.citations == []

    joined = target_from_config({"type": "python", "entry": "tests.targets.agents:chunks"})
    [streamed] = asyncio.run(
        run_cases([case("c3", question="Q?")], joined, new_log(tmp_path / "3"))
    )
    assert streamed.output == "first second"


def test_http_endpoint_with_a_start_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_TOKEN", "t0k3n")
    port = free_port()
    config = {
        "type": "http",
        "url": f"http://127.0.0.1:{port}/ask",
        "start": f"{sys.executable} {HERE / 'server.py'} {port}",
        "headers": {"Authorization": "Bearer ${AGENT_TOKEN}"},
        "body": {"query": "{{question}}", "context": {"facts": "Facts: {{facts}}"}},
        "answer": "$.data.text",
        "citations": "$.sources[*].ref",
    }
    target = target_from_config(config)
    cases = [case("c1", question="Q1", facts="F1"), case("c2", question="Q2", facts="F2")]

    results = asyncio.run(run_cases(cases, target, new_log(tmp_path)))

    assert [r.output for r in results] == [
        'echo {"context": {"facts": "Facts: F1"}, "query": "Q1"} auth=Bearer t0k3n',
        'echo {"context": {"facts": "Facts: F2"}, "query": "Q2"} auth=Bearer t0k3n',
    ]
    assert results[0].citations == ["E2023/1-K2024/2", "E2022/7-K2023/9"]
    assert isinstance(target, HttpTarget) and target.process is None  # stopped at the end

    deployed = serve(0)
    threading.Thread(target=deployed.serve_forever, daemon=True).start()
    try:
        as_is = target_from_config(
            {**config, "start": None, "url": f"http://127.0.0.1:{deployed.server_port}/ask"}
        )
        [result] = asyncio.run(
            run_cases(
                [case("c3", question="Q3", facts="F3")], as_is, new_log(tmp_path / "deployed")
            )
        )
        assert result.error is None and (result.output or "").startswith("echo")
    finally:
        deployed.shutdown()


def test_command(tmp_path: Path):
    target = target_from_config(
        {
            "type": "command",
            "run": f"{sys.executable} {HERE / 'command_agent.py'} --question {{question}}",
        }
    )
    cases = [case("ok", question="Is the clause valid?"), case("bad", question="fail")]

    results = asyncio.run(run_cases(cases, target, new_log(tmp_path)))

    by_id = {result.case_id: result for result in results}
    assert by_id["ok"].output == "Answer to: Is the clause valid?"
    assert by_id["ok"].error is None
    assert by_id["bad"].output is None
    assert (
        by_id["bad"].error == "CommandFailed: the command exited with 3: the model is unreachable"
    )


def test_checked_before_a_run(tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    config.write_text(
        "target:\n  type: python\n  entry: tests.targets.agents:answer\n", encoding="utf-8"
    )

    checked = CliRunner().invoke(
        main, ["target", "check", "--config", str(config), "--question", "Is it valid?"]
    )

    assert checked.exit_code != 0  # the agent needs `facts`, which the sample case lacks
    assert "the sample case failed" in checked.output
    assert "missing 1 required positional argument: 'facts'" in checked.output

    config.write_text(
        "target:\n  type: python\n  entry: tests.targets.agents:plain\n", encoding="utf-8"
    )
    checked = CliRunner().invoke(main, ["target", "check", "--config", str(config)])
    assert checked.exit_code == 0, checked.output
    assert "answer     The court relied on" in checked.output
    assert "steps      0 captured" in checked.output


def test_concurrency_and_async(tmp_path: Path):
    target = target_from_config({"type": "python", "entry": "tests.targets.agents:concurrent"})
    cases = [case(f"c{n}", question=f"q{n}") for n in range(16)]

    results = asyncio.run(run_cases(cases, target, new_log(tmp_path), max_concurrency=8))

    spans = [(s.started, s.ended) for r in results for s in r.steps if s.kind is StepKind.TOOL]
    moments = sorted([(start, 1) for start, _ in spans] + [(end, -1) for _, end in spans])
    running = peak = 0
    for _, change in moments:
        running += change
        peak = max(peak, running)
    assert peak == 8
    for result in results:
        own = result.case_id.replace("c", "q")
        assert [step.name for step in result.steps] == [f"tool-for-{own}", f"model-for-{own}"]


def test_a_crashing_agent_costs_one_case_not_the_run(tmp_path: Path):
    target = target_from_config(
        {"type": "python", "entry": "tests.targets.agents:crashes_on_request"}
    )
    cases = [case("a", question="first"), case("b", question="crash"), case("c", question="last")]

    results = {r.case_id: r for r in asyncio.run(run_cases(cases, target, new_log(tmp_path)))}

    assert results["a"].output == "answered first"
    assert results["b"].error == "WorkerDied: the agent's process exited with 3 during this case"
    assert results["c"].output == "answered last"
