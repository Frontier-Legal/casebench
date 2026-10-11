"""Every model call, tool call and backend step captured with no change to the agent's code:
functions named in the config."""

import hashlib
import shutil
from pathlib import Path

from click.testing import CliRunner

from casebench.capture.step import StepKind
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import RunLog
from casebench.suites.freeze import freeze

AGENT = Path(__file__).resolve().parent / "rerank_agent.py"


def prepare(tmp_path: Path, functions: str) -> tuple[Path, Path, Path]:
    agent = tmp_path / "agent.py"
    shutil.copy(AGENT, agent)
    config = tmp_path / "casebench.yaml"
    config.write_text(
        f"target: {{type: python, entry: unused:unused}}\ncapture:\n  functions:\n{functions}",
        encoding="utf-8",
    )
    case = Case(
        id="c1",
        task=Task.model_validate({"type": "qa", "question": "Valid?"}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )
    freeze("named", [case], tmp_path / "suite")
    return agent, config, tmp_path / "suite"


def invoke(agent: Path, config: Path, suite: Path, runs: Path):
    return CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(suite),
            "--config",
            str(config),
            "--python",
            str(agent),
            "--runs-dir",
            str(runs),
            "--run-id",
            "r1",
        ],
    )


def test_a_function_named_in_the_config(tmp_path: Path):
    agent, config, suite = prepare(
        tmp_path,
        (
            "    - {function: 'agent.py:search', step: retrieval, doc_ids_out: '$.result[*].id'}\n"
            "    - function: 'agent.py:rerank'\n"
            "      step: rerank\n"
            "      doc_ids_in: '$.arguments.candidates[*].id'\n"
            "      doc_ids_out: '$.result[*].id'\n"
        ),
    )
    before = hashlib.sha256(agent.read_bytes()).hexdigest()

    ran = invoke(agent, config, suite, tmp_path / "runs")

    assert ran.exit_code == 0, ran.output
    [result] = RunLog(tmp_path / "runs" / "r1").results()
    assert result.documents == ["tr-1", "tr-3"]
    search = next(s for s in result.steps if s.kind is StepKind.RETRIEVAL)
    rerank = next(s for s in result.steps if s.kind is StepKind.RERANK)
    assert (search.name, search.doc_ids_out) == ("search", ["tr-1", "tr-2", "tr-3"])
    assert (rerank.name, rerank.doc_ids_in, rerank.doc_ids_out) == (
        "rerank",
        ["tr-1", "tr-2", "tr-3"],
        ["tr-1", "tr-3"],
    )
    assert rerank.duration_ms is not None and rerank.note is None
    assert hashlib.sha256(agent.read_bytes()).hexdigest() == before


def test_a_name_the_agent_does_not_have_stops_the_run_before_any_case(tmp_path: Path):
    agent, config, suite = prepare(tmp_path, "    - {function: 'agent.py:rerank_v2'}\n")

    ran = invoke(agent, config, suite, tmp_path / "runs")

    assert ran.exit_code != 0
    assert "the agent did not start" in ran.output and "rerank_v2" in ran.output
    assert RunLog(tmp_path / "runs" / "r1").results() == []
