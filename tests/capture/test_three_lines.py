"""Three lines connect a Python agent in its own process (decision 0062)."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import anthropic
import httpx
import httpx2
import pytest
import requests
from click.testing import CliRunner
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import casebench as cb
from casebench.capture.step import StepKind
from casebench.cli import main
from casebench.runs.log import RESULTS_FILE, RunLog
from tests.report.suites import frozen, mixed

# A client's facts, as a tool call's arguments carry them.
CLIENT = "Ayşe Yılmaz"


def message(content: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": content,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 120, "output_tokens": 30},
    }


class Upstream(BaseHTTPRequestHandler):
    """A model API, a Qdrant store and an agent's HTTP endpoint, as their real ones answer."""

    paths: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        Upstream.paths.append(self.path)
        if self.path.endswith("/points/search"):
            reply: Any = {"result": [{"id": "dec-1", "score": 0.9}], "status": "ok"}
        elif self.path == "/ask":
            # An endpoint gets the question alone, as `{"question": ...}`.
            reply = {"answer": f"Upheld, as asked: {body['question'][:12]}"}
        elif body.get("tools"):
            call = {"type": "tool_use", "id": "t1", "name": "search", "input": {"party": CLIENT}}
            reply = message([call])
        else:
            reply = message([{"type": "text", "text": "Reversed."}])
        payload = json.dumps(reply, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


@pytest.fixture
def upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "agent-key")
    frozen(mixed(3), tmp_path / "suite")
    Upstream.paths = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def an_agent(url: str, tools: bool = False):
    """An agent built in memory, as in a notebook: it searches its store, then asks its model."""
    client = anthropic.Anthropic(base_url=url)

    def answer(question: str, facts: str) -> str:
        httpx.post(f"{url}/collections/law/points/search", json={"vector": [0.1], "limit": 1})
        asked: dict[str, Any] = {"tools": [{"name": "search", "input_schema": {}}]} if tools else {}
        client.messages.create(
            model="claude-sonnet-5-5",
            max_tokens=100,
            messages=[{"role": "user", "content": facts}],
            **asked,
        )
        return "Reversed." if "appeal" in facts else "Upheld."

    return answer


def steps_of(run: Path) -> list[list[Any]]:
    return [result.steps for result in RunLog(run).results()]


def test_three_lines(upstream: str, capsys: pytest.CaptureFixture[str]):
    agent = an_agent(upstream)

    cb.instrument()
    run = cb.run(agent, suite="suite")

    printed = capsys.readouterr().out
    log = RunLog(run)
    assert len(log.results()) == 3 and log.score_sets()
    assert "open it in the workbench: casebench ui" in printed
    for steps in steps_of(run):
        kinds = [(step.kind, step.doc_ids_out, step.model) for step in steps]
        assert (StepKind.RETRIEVAL, ["dec-1"], None) in kinds
        assert (StepKind.LLM, [], "claude-sonnet-5-5") in kinds
    # After the run, calls go where they always went, and nothing is recorded.
    assert httpx.post(f"{upstream}/v1/messages", json={}).json()["model"] == "claude-sonnet-5-5"


def test_a_notebook_awaits_the_run(upstream: str):
    agent = an_agent(upstream)

    async def notebook_cell() -> Path:
        cb.instrument()
        return await cb.arun(agent, suite="suite")

    run = asyncio.run(notebook_cell())

    assert len(RunLog(run).results()) == 3


def test_never_hijacks_the_apps_telemetry(upstream: str, capsys: pytest.CaptureFixture[str]):
    # The app's own provider and exporter, set up as an app does at start.
    exported = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exported))
    trace.set_tracer_provider(provider)
    agent = an_agent(upstream)

    libraries = cb.instrument()
    run = cb.run(agent, suite="suite")

    assert trace.get_tracer_provider() is provider
    assert exported.get_finished_spans() == ()
    assert all(steps for steps in steps_of(run))  # Casebench still captured
    assert {"httpx2", "httpx", "requests"} <= set(libraries)
    assert (
        "casebench: recording calls made through httpx2, httpx, requests" in capsys.readouterr().out
    )


def test_http_service_in_any_language(upstream: str):
    ran = CliRunner().invoke(
        main, ["run", "--endpoint", f"{upstream}/ask", "--suite", "suite", "--run-id", "e"]
    )

    log = RunLog(Path(".casebench") / "runs" / "e")
    assert ran.exit_code == 0, ran.output
    assert Upstream.paths.count("/ask") == 3
    assert {r.output for r in log.results()} == {"Upheld, as asked: How did the "}
    # Scored: the one upheld case is right, the two reversed ones wrong.
    assert sorted(s.value for s in RunLog.read_scores(log.score_sets()[-1])) == [0.0, 0.0, 1.0]


def test_content_stays_home(upstream: str):
    agent = an_agent(upstream, tools=True)
    cb.instrument()

    kept_out = cb.run(agent, suite="suite", run_id="default")
    Path("casebench.yaml").write_text("capture: {content: true}\n", encoding="utf-8")
    kept_in = cb.run(agent, suite="suite", run_id="content")

    stored = (kept_out / RESULTS_FILE).read_text(encoding="utf-8")
    [calls] = {
        len(step.requested_tools) for steps in steps_of(kept_out) for step in steps if step.model
    }
    assert calls == 1  # the tool call is recorded, by its id and name
    assert CLIENT not in stored
    assert '"input_tokens":120' in stored and '"model":"claude-sonnet-5-5"' in stored
    assert CLIENT in (kept_in / RESULTS_FILE).read_text(encoding="utf-8")


@pytest.mark.parametrize("library", ["httpx2", "httpx", "requests"])
def test_conformance_per_library(upstream: str, library: str):
    send = {"httpx2": httpx2.post, "httpx": httpx.post, "requests": requests.post}[library]

    def agent(question: str) -> str:
        reply = send(
            f"{upstream}/v1/messages",
            json={"model": "claude-sonnet-5-5", "max_tokens": 10, "messages": []},
            headers={"x-api-key": "agent-key", "anthropic-version": "2023-06-01"},
        )
        return reply.json()["content"][0]["text"]

    assert library in cb.instrument()
    run = cb.run(agent, suite="suite", run_id=library)

    for steps in steps_of(run):
        [call] = [step for step in steps if step.kind is StepKind.LLM]
        assert (call.provider, call.model, call.input_tokens, call.output_tokens) == (
            "anthropic",
            "claude-sonnet-5-5",
            120,
            30,
        )
