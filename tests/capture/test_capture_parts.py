"""The proxy's parts in detail: attribution, pairing, gaps, redaction, routes, streams."""

from pathlib import Path

from click.testing import CliRunner

from casebench.capture.assemble import gaps, paired_tools
from casebench.capture.config import CaptureConfig, routes_for
from casebench.capture.parsers.openai import Parser as OpenAiParser
from casebench.capture.proxy.redact import redact_url
from casebench.capture.proxy.sse import parse_events
from casebench.capture.recorder import Recorder
from casebench.capture.step import HttpExchange, Step, StepKind, ToolCall, ToolResult
from casebench.cli import main


def exchange(started: float) -> HttpExchange:
    return HttpExchange(
        method="POST", url="http://x/v1/messages", status=200, started=started, ended=started + 1
    )


def test_an_exchange_without_trace_context_belongs_to_the_only_running_case():
    recorder = Recorder()
    recorder.begin("c1")
    recorder.add(exchange(1.0), None)
    assert [e.started for e in recorder.end("c1")] == [1.0]


def test_with_two_cases_running_and_no_trace_context_an_exchange_stays_unattributed():
    recorder = Recorder()
    first = recorder.begin("c1")
    recorder.begin("c2")
    recorder.add(exchange(1.0), None)
    recorder.add(exchange(2.0), first)
    assert [e.started for e in recorder.end("c1")] == [2.0]
    assert recorder.end("c2") == []
    assert [e.started for e in recorder.unattributed] == [1.0]


def test_a_tool_call_is_paired_with_its_result_once():
    asked = Step(
        kind=StepKind.LLM,
        started=0.0,
        ended=1.0,
        requested_tools=[ToolCall(id="t1", name="search", arguments={"q": "x"})],
    )
    answered = Step(
        kind=StepKind.LLM, started=3.5, ended=4.0, tool_results=[ToolResult(id="t1", size=42)]
    )
    repeated = Step(
        kind=StepKind.LLM, started=5.0, ended=6.0, tool_results=[ToolResult(id="t1", size=42)]
    )
    [tool] = paired_tools([asked, answered, repeated])
    assert (tool.name, tool.arguments, tool.result_size, tool.duration_ms) == (
        "search",
        {"q": "x"},
        42,
        2500.0,
    )


def test_time_no_step_covers_is_a_gap_between_the_steps_around_it():
    first = Step(kind=StepKind.LLM, model="m", started=0.0, ended=1.0)
    overlapping = Step(kind=StepKind.RETRIEVAL, name="search", started=0.5, ended=1.2)
    later = Step(kind=StepKind.LLM, model="m", started=4.2, ended=5.0)
    [gap] = gaps([first, overlapping, later])
    assert (gap.name, gap.duration_ms) == ("between retrieval search and llm m", 3000.0)


def test_secret_query_parameters_are_never_recorded():
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/m:generateContent?key=AIza&alt=sse"
    )
    assert redact_url(url) == (
        "https://generativelanguage.googleapis.com/v1beta/models/m:generateContent"
        "?key=REDACTED&alt=sse"
    )


def test_a_stream_is_read_event_by_event():
    raw = b'event: a\ndata: {"n": 1}\n\n: comment\ndata: {"n": 2}\n\ndata: [DONE]\n\n'
    assert parse_events(raw) == [{"n": 1}, {"n": 2}]


def test_a_stream_is_asked_for_its_usage():
    prepared = OpenAiParser().prepare({"model": "m", "stream": True})
    assert prepared["stream_options"] == {"include_usage": True}
    assert OpenAiParser().prepare({"model": "m"}) == {"model": "m"}


def test_config_routes_lay_over_the_parsers_defaults():
    routes = {
        r.name: r
        for r in routes_for(
            CaptureConfig(
                routes=[
                    {"name": "anthropic", "upstream": "http://localhost:9"},
                    {
                        "name": "search",
                        "upstream": "http://localhost:6333",
                        "doc_ids": "$.result[*].id",
                    },
                ]
            )
        )
    }
    assert routes["anthropic"].upstream == "http://localhost:9"
    assert routes["anthropic"].parser == "anthropic"
    assert routes["anthropic"].env == "ANTHROPIC_BASE_URL"
    assert routes["openai"].upstream == "https://api.openai.com"
    assert routes["search"].parser is None


def test_the_proxy_prints_the_lines_an_agent_already_running_needs(tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    config.write_text(
        "target: {type: command, run: echo}\ncapture: {port: 8899}\n", encoding="utf-8"
    )
    printed = CliRunner().invoke(main, ["proxy", "env", "--config", str(config)])
    assert "ANTHROPIC_BASE_URL=http://127.0.0.1:8899/anthropic" in printed.output
    assert "OPENAI_BASE_URL=http://127.0.0.1:8899/openai/v1" in printed.output

    config.write_text("target: {type: command, run: echo}\n", encoding="utf-8")
    refused = CliRunner().invoke(main, ["proxy", "env", "--config", str(config)])
    assert refused.exit_code != 0 and "set capture.port" in refused.output
