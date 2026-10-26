"""Every model call, tool call and backend step captured with no change to the agent's code:
the recording proxy tier."""

import asyncio
import socket
import sys
from pathlib import Path

import httpx2
from click.testing import CliRunner

from casebench.capture.config import CaptureConfig, routes_for
from casebench.capture.redirect import FOLLOW, followed
from casebench.capture.session import CaptureSession
from casebench.capture.step import NO_DIAGNOSTIC, StepKind
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.runner import run_cases
from casebench.suites.freeze import freeze
from casebench.targets.load import target_from_config
from tests.capture.openai_upstream import start_openai
from tests.capture.upstreams import start_upstream

AGENT = Path(__file__).resolve().parent / "plain_http_agent.py"


def case(case_id: str, question: str) -> Case:
    return Case(
        id=case_id,
        task=Task.model_validate({"type": "qa", "question": question}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )


def run(
    tmp_path: Path,
    routes: list[dict[str, str]],
    *,
    concurrency: int = 1,
    pass_trace: bool = False,
    monkeypatch=None,
) -> list[Result]:
    if pass_trace and monkeypatch is not None:
        monkeypatch.setenv("PASS_TRACE", "1")
    session = CaptureSession(routes_for(CaptureConfig(routes=routes)))
    target = target_from_config(
        {"type": "command", "run": f"{sys.executable} {AGENT} {{question}}"}
    )
    log = RunLog.create(
        tmp_path / "run", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="command")
    )
    cases = [case("c1", "Is the dismissal valid?"), case("c2", "Is the notice valid?")]
    return asyncio.run(run_cases(cases, target, log, capture=session, max_concurrency=concurrency))


def upstream_routes(base: str, *, doc_ids: str | None = "$.result[*].id") -> list[dict[str, str]]:
    search = {"name": "search", "upstream": base, "env": "SEARCH_URL"}
    if doc_ids:
        search["doc_ids"] = doc_ids
    return [{"name": "anthropic", "upstream": base}, search]


def test_any_language_through_the_proxy(tmp_path: Path):
    upstream = start_upstream()
    base = f"http://127.0.0.1:{upstream.server_port}"
    try:
        results = run(tmp_path, upstream_routes(base))
    finally:
        upstream.shutdown()

    for result in results:
        assert result.error is None, result.error
        assert result.output == "The dismissal is invalid."
        assert "secret-key" not in result.model_dump_json()
        calls = [s for s in result.steps if s.kind is StepKind.LLM]
        assert [(s.provider, s.model, s.input_tokens, s.output_tokens) for s in calls] == [
            ("anthropic", "claude-sonnet-5-5", 120, 30),  # streamed, tokens still reported
            ("anthropic", "claude-sonnet-5-5", 200, 40),
        ]
        assert all(s.duration_ms is not None and s.duration_ms > 0 for s in calls)
        [tool] = [s for s in result.steps if s.kind is StepKind.TOOL]
        assert (tool.name, tool.arguments, tool.result_size) == (
            "search",
            {"query": "dismissal"},
            len("tr-1, tr-2"),
        )
        assert tool.duration_ms is not None and tool.duration_ms >= 0


def test_a_backend_through_the_proxy(tmp_path: Path):
    upstream = start_upstream()
    base = f"http://127.0.0.1:{upstream.server_port}"
    try:
        [with_ids, _] = run(tmp_path / "a", upstream_routes(base))
        [without, _] = run(tmp_path / "b", upstream_routes(base, doc_ids=None))
    finally:
        upstream.shutdown()

    [search] = [s for s in with_ids.steps if s.kind is StepKind.RETRIEVAL]
    assert (search.name, search.doc_ids_out, search.note) == ("search", ["tr-1", "tr-2"], None)
    [blind] = [s for s in without.steps if s.kind is StepKind.RETRIEVAL]
    assert (blind.doc_ids_out, blind.note) == ([], NO_DIAGNOSTIC)


def test_concurrent_cases_keep_their_own_calls_when_the_agent_passes_trace_context(
    tmp_path: Path, monkeypatch
):
    upstream = start_upstream()
    base = f"http://127.0.0.1:{upstream.server_port}"
    try:
        results = run(
            tmp_path, upstream_routes(base), concurrency=2, pass_trace=True, monkeypatch=monkeypatch
        )
    finally:
        upstream.shutdown()

    for result in results:
        assert len([s for s in result.steps if s.kind is StepKind.LLM]) == 2
        assert len([s for s in result.steps if s.kind is StepKind.RETRIEVAL]) == 1


def test_a_started_http_agent_runs_under_the_capture_wrapper(tmp_path: Path):
    upstream = start_upstream()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = Path(__file__).resolve().parent / "http_agent_server.py"
    target = target_from_config(
        {
            "type": "http",
            "url": f"http://127.0.0.1:{port}/ask",
            "start": f"{sys.executable} {server} {port}",
            "body": {"question": "{{question}}"},
            "answer": "$.answer",
        }
    )
    session = CaptureSession(
        routes_for(
            CaptureConfig(
                routes=[
                    {"name": "anthropic", "upstream": f"http://127.0.0.1:{upstream.server_port}"}
                ]
            )
        )
    )
    log = RunLog.create(
        tmp_path / "run", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="http")
    )
    try:
        [result] = asyncio.run(run_cases([case("c1", "Valid?")], target, log, capture=session))
    finally:
        upstream.shutdown()

    assert result.output == "The dismissal is invalid."
    [call] = [s for s in result.steps if s.kind is StepKind.LLM]
    assert (call.provider, call.input_tokens, call.output_tokens) == ("anthropic", 200, 40)


def test_a_streamed_call_a_python_agent_sends_to_an_openai_compatible_host_reports_its_tokens():
    upstream = start_openai()
    session = CaptureSession(routes_for(None))
    asked = {"model": "gpt-5", "stream": True, "messages": [{"role": "user", "content": "Q?"}]}

    async def call() -> list:
        await session.start()
        try:
            session.recorder.begin("c1")
            here = f"http://127.0.0.1:{upstream.server_port}/v1/chat/completions"
            url = followed(here, session.env[FOLLOW])
            assert url is not None
            async with httpx2.AsyncClient() as client:
                (await client.post(url, json=asked)).raise_for_status()
            return session.recorder.end("c1")
        finally:
            await session.stop()

    try:
        [exchange] = asyncio.run(call())
    finally:
        upstream.shutdown()

    [step] = session.parse(exchange)
    assert (step.provider, step.input_tokens, step.output_tokens) == ("openai", 30, 4)
    added = exchange.request_body.pop("stream_options")
    assert (added, exchange.request_body) == ({"include_usage": True}, asked)


def test_a_route_whose_variable_already_points_at_the_proxy_forwards_to_its_upstream(
    monkeypatch,
):
    upstream = start_upstream()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    # The shell exported the lines `casebench proxy env` prints for this port.
    monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{port}/anthropic")
    base = f"http://127.0.0.1:{upstream.server_port}"
    session = CaptureSession(routes_for(CaptureConfig(routes=upstream_routes(base))), port)
    asked = {"model": "claude-sonnet-5-5", "max_tokens": 512, "messages": []}

    async def call() -> httpx2.Response:
        await session.start()
        try:
            async with httpx2.AsyncClient() as client:
                return await client.post(
                    f"{session.env['ANTHROPIC_BASE_URL']}/v1/messages", json=asked
                )
        finally:
            await session.stop()

    try:
        answered = asyncio.run(call())
    finally:
        upstream.shutdown()

    assert session.routes["anthropic"].upstream == base
    assert answered.json()["content"][0]["text"] == "The dismissal is invalid."


def test_a_run_says_how_many_calls_it_could_not_attribute_to_a_case(tmp_path: Path):
    upstream = start_upstream()
    stages = tmp_path / "stages"
    stages.mkdir()
    agent = Path(__file__).resolve().parent / "concurrent_agent.py"
    config = tmp_path / "casebench.yaml"
    config.write_text(
        f"target: {{type: command, run: '{sys.executable} {agent} {stages} 2'}}\n"
        "capture:\n  routes:\n"
        f"    - {{name: anthropic, upstream: 'http://127.0.0.1:{upstream.server_port}'}}\n",
        encoding="utf-8",
    )
    suite = tmp_path / "suite"
    freeze("concurrent", [case("c1", "Valid?"), case("c2", "Void?")], suite)
    try:
        printed = CliRunner().invoke(
            main,
            [
                "run",
                *("--suite", str(suite), "--config", str(config)),
                *("--max-concurrency", "2", "--runs-dir", str(tmp_path / "runs")),
                *("--run-id", "r1"),
            ],
        )
    finally:
        upstream.shutdown()

    assert printed.exit_code == 0, printed.output
    assert "2 calls could not be attributed to a case" in printed.output
    assert RunLog(tmp_path / "runs" / "r1").info.unattributed_calls == 2


def test_a_capture_routes_upstream_may_name_a_variable(tmp_path: Path, monkeypatch):
    upstream = start_upstream()
    monkeypatch.setenv("MODEL_URL", f"http://127.0.0.1:{upstream.server_port}")
    try:
        results = run(tmp_path, upstream_routes("${MODEL_URL}"))
    finally:
        upstream.shutdown()

    for result in results:
        assert result.error is None, result.error
        assert result.output == "The dismissal is invalid."
        assert len([s for s in result.steps if s.kind is StepKind.LLM]) == 2
