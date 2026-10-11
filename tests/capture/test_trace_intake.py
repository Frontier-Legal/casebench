"""Every model call, tool call and backend step captured with no change to the agent's code:
traces a team already emits."""

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.capture.otlp.decode import from_json
from casebench.capture.step import NO_DIAGNOSTIC, StepKind
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import RunLog
from casebench.suites.freeze import freeze

AGENT = Path(__file__).resolve().parent / "traced_agent.py"


def test_traces_i_already_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    agent = tmp_path / "agent.py"
    shutil.copy(AGENT, agent)
    config = tmp_path / "casebench.yaml"
    config.write_text(
        "target: {type: python, entry: agent.py}\ncapture: {traces: true}\n", encoding="utf-8"
    )
    cases = [
        Case(
            id=q,
            task=Task.model_validate({"type": "qa", "question": q}),
            reference=Reference(source=ReferenceSource.LAWYER),
            metrics=[],
        )
        for q in ("q1", "q2")
    ]
    freeze("traced", cases, tmp_path / "suite")

    ran = CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(tmp_path / "suite"),
            "--config",
            str(config),
            "--max-concurrency",
            "2",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--run-id",
            "r1",
        ],
    )

    assert ran.exit_code == 0, ran.output
    for result in RunLog(tmp_path / "runs" / "r1").results():
        q = result.case_id
        by_name = {s.name: s for s in result.steps}
        assert by_name["retrieve"].kind is StepKind.RETRIEVAL
        assert by_name["retrieve"].doc_ids_out == [f"{q}-a", f"{q}-b", f"{q}-c"]
        assert by_name["rerank"].kind is StepKind.RERANK
        assert by_name["rerank"].doc_ids_in == [f"{q}-a", f"{q}-b", f"{q}-c"]
        assert by_name["rerank"].doc_ids_out == [f"{q}-a"]
        assert by_name["statutes"].doc_ids_out == [f"{q}-law"]
        assert (by_name["memory"].doc_ids_out, by_name["memory"].note) == ([], NO_DIAGNOSTIC)
        model = by_name["chat model-x"]
        assert (model.kind, model.provider, model.model, model.input_tokens) == (
            StepKind.LLM,
            "national",
            "model-x",
            321,
        )


def test_otlp_json_is_read_with_hex_ids_and_string_integers():
    body = json.dumps(
        {
            "resourceSpans": [
                {
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "5B8EFFF798038103D269B633813FC60C",
                                    "name": "chat",
                                    "startTimeUnixNano": "1760000000000000000",
                                    "endTimeUnixNano": "1760000001500000000",
                                    "attributes": [
                                        {
                                            "key": "gen_ai.operation.name",
                                            "value": {"stringValue": "chat"},
                                        },
                                        {
                                            "key": "gen_ai.usage.input_tokens",
                                            "value": {"intValue": "42"},
                                        },
                                        {
                                            "key": "tags",
                                            "value": {
                                                "arrayValue": {"values": [{"stringValue": "a"}]}
                                            },
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ).encode()

    [span] = from_json(body)

    assert span.trace_id == "5b8efff798038103d269b633813fc60c"
    assert span.ended - span.started == pytest.approx(1.5)
    assert span.attributes == {
        "gen_ai.operation.name": "chat",
        "gen_ai.usage.input_tokens": 42,
        "tags": ["a"],
    }
