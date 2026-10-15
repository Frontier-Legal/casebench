"""A run reports what it spent, per model, for the agent and for the judge (decision 0051)."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from casebench.capture.step import Step, StepKind
from casebench.cli import main
from casebench.judge.config import JudgeConfig, Price
from casebench.judge.families import AgentModel
from casebench.judge.memo import MEMO_FILE
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.spend import run_spend
from casebench.setup.catalog import prices
from tests.judge.fake_judge import start_fake_judge
from tests.report.suites import criteria_case, frozen

AGENTS = Path(__file__).parent / "agents.py"
JUDGE_PRICE = {"input": 3.0, "output": 15.0}


def scored(tmp_path: Path, port: int):
    judge = {
        "provider": "anthropic",
        "model": "judge-model",
        "options": {"base_url": f"http://127.0.0.1:{port}", "max_tokens": 1024},
        "price": JUDGE_PRICE,
    }
    (tmp_path / "casebench.yaml").write_text(yaml.safe_dump({"judge": judge}), encoding="utf-8")
    # Three criteria, so three different questions to the judge.
    words = ("upheld", "decision", "the")
    frozen(
        [criteria_case(n, {f"Mentions {w}": 1}) for n, w in enumerate(words, 1)],
        tmp_path / "suite",
    )
    return CliRunner().invoke(
        main,
        ["run", "--suite", str(tmp_path / "suite"), "--config", str(tmp_path / "casebench.yaml"),
         "--python", f"{AGENTS}:upheld", "--runs-dir", str(tmp_path / "runs"), "--run-id", "r"],
    )  # fmt: skip


def spend_of(tmp_path: Path) -> dict[str, Any]:
    report = json.loads((tmp_path / "runs" / "r" / "report.json").read_text(encoding="utf-8"))
    return report["spend"]


def test_a_run_reports_what_it_spent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_fake_judge()
    first = scored(tmp_path, server.server_port)
    again = scored(tmp_path, server.server_port)
    server.shutdown()

    assert first.exit_code == 0, first.output
    spend = spend_of(tmp_path)
    [judge] = [m for m in spend["models"] if m["whose"] == "judge"]
    # The fake judge reports one input and one output token per call: three cases graded.
    assert (judge["model"], judge["calls"]) == ("anthropic/judge-model", 3)
    assert judge["cost"] == pytest.approx(3 * (3.0 + 15.0) / 1_000_000)
    assert spend["judge"] == spend["total"] == pytest.approx(judge["cost"])
    assert "spend: $0.0001 · agent $0.00 · judge $0.0001" in first.output
    # Scoring again reads the kept replies: nothing new is spent, and the run still says what it
    # cost to grade.
    assert again.exit_code == 0, again.output
    assert spend_of(tmp_path) == spend
    shown = CliRunner().invoke(main, ["report", str(tmp_path / "runs" / "r")])
    assert re.search(r"judge anthropic/judge-model +3 calls", shown.output), shown.output


def test_the_agents_calls_are_priced_per_model(tmp_path: Path):
    log = RunLog.create(
        tmp_path / "r", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="t")
    )

    def step(model: str, tokens_in: int, tokens_out: int) -> Step:
        return Step(
            kind=StepKind.LLM, model=model, input_tokens=tokens_in, output_tokens=tokens_out
        )

    log.append(Result(case_id="a", output="x", steps=[step("small-model-2026-01-01", 1000, 100)]))
    log.append(
        Result(
            case_id="b",
            output="y",
            steps=[step("small-model-2026-01-01", 3000, 300), step("unlisted-model", 500, 50)],
        )
    )
    memo = tmp_path / "r" / MEMO_FILE
    usage = {"provider": "openai", "model": "big-judge", "input_tokens": 2000, "output_tokens": 200}
    memo.write_text(
        json.dumps({"key": "k1", "reply": [], "usage": usage})
        + "\n"
        + json.dumps({"key": "k0", "reply": []})
        + "\n",
        encoding="utf-8",
    )

    spend = run_spend(
        log,
        [AgentModel(model="small-model", family="small", price=Price(input=1.0, output=4.0))],
        [JudgeConfig(provider="openai", model="big-judge", price=Price(input=10.0, output=30.0))],
    )

    rows = {(m.whose, m.model): m for m in spend.models}
    small = rows[("agent", "small-model-2026-01-01")]
    assert (small.calls, small.input_tokens, small.output_tokens) == (2, 4000, 400)
    assert small.cost == pytest.approx((4000 * 1.0 + 400 * 4.0) / 1_000_000)
    assert rows[("agent", "unlisted-model")].cost is None
    assert rows[("judge", "openai/big-judge")].cost == pytest.approx((2000 * 10 + 200 * 30) / 1e6)
    # A reply kept before calls recorded their tokens is counted as a call of an unknown model.
    assert rows[("judge", "unknown model")].calls == 1
    assert spend.agent == pytest.approx(small.cost)
    assert spend.total == pytest.approx(spend.agent + spend.judge)
    assert spend.unpriced == ["agent unlisted-model", "judge unknown model"]


def test_init_prices_the_agents_models_from_the_catalog():
    qwen = {"family": "qwen", "cost": {"input": 0.9, "output": 0.9}}
    catalog = {
        "fireworks": {"models": {"accounts/fireworks/models/qwen-big": qwen, "no-price": {}}}
    }

    found = prices(catalog, ["qwen-big", "no-price", "unknown"])

    assert found == {"qwen-big": {"input": 0.9, "output": 0.9}}
