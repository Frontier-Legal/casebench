"""Every model call, tool call and backend step captured with no change to the agent's code:
the recording proxy tier."""

import asyncio
import socket
import sys
from pathlib import Path

from casebench.capture.config import CaptureConfig, routes_for
from casebench.capture.session import CaptureSession
from casebench.capture.step import NO_DIAGNOSTIC, StepKind
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.runner import run_cases
from casebench.targets.load import target_from_config
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
        # The arguments are dropped before the result is stored (decision 0062).
        assert (tool.name, tool.arguments, tool.result_size) == ("search", None, len("tr-1, tr-2"))
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
