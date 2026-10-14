"""Model settings chosen by measurement: reasoning effort and output limits for the judge and
extraction (decision 0038)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.providers.builtin.anthropic import Provider as Anthropic
from casebench.providers.builtin.azure import Provider as Azure
from casebench.providers.builtin.bedrock import Provider as Bedrock
from casebench.providers.builtin.google import Provider as Google
from casebench.providers.builtin.openai import Provider as OpenAI
from casebench.providers.interface import Message
from casebench.providers.settings import SettingNotTaken, build
from tests.extract.decisions import DECISIONS
from tests.extract.fake_models import UNOFFERED, FakeModels, start_fake_models
from tests.report.suites import frozen, mixed

ASKED = [Message(role="system", content="s"), Message(role="user", content="u")]
AGENTS = Path(__file__).parents[1] / "report" / "agents.py"


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def config_text(port: int, store: Path, model_options: str = "") -> str:
    """Two priced extraction models with an output limit; `model_options` adds settings."""
    options = f"{{base_url: 'http://127.0.0.1:{port}', max_tokens: 2048{model_options}}}"
    price = "{input: 1.0, output: 4.0}"
    return (
        f"corpus: {{connector: folder, options: {{path: '{store.as_posix()}'}}}}\n"
        "extract:\n  models:\n"
        f"    - {{provider: anthropic, model: model-a, options: {options}, price: {price}}}\n"
        f"    - {{provider: anthropic, model: model-b, options: {options}, price: {price}}}\n"
    )


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    store = tmp_path / "decisions"
    store.mkdir()
    for decision_id, (country, court, level, day, text) in DECISIONS.items():
        record = {
            "id": decision_id,
            "jurisdiction": country,
            "court": court,
            "level": level,
            "date": day,
            "text": text,
        }
        (store / f"{decision_id}.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8"
        )
    server = start_fake_models()
    config = tmp_path / "casebench.yaml"
    config.write_text(config_text(server.server_port, store), encoding="utf-8")
    yield tmp_path, config, server.server_port, store
    server.shutdown()


def test_a_setting_reaches_the_provider(workspace):
    _, config, port, store = workspace
    openai = OpenAI(reasoning_effort="low", temperature=0.0).request(ASKED, "m", "k").body
    anthropic = Anthropic(max_tokens=4096, reasoning_effort="low", thinking_budget=2048)
    google = Google(reasoning_effort="low", thinking_budget=2048, temperature=0.0)
    bedrock = Bedrock(temperature=0.0, model_fields={"reasoning_effort": "low"})
    azure = Azure(reasoning_effort="low", temperature=0.0).create(ASKED, "deployment")
    with pytest.raises(SettingNotTaken) as refused:
        build(Anthropic, "anthropic", {"max_tokens": 4096, "temperature": 0.0})

    config.write_text(config_text(port, store, ", reasoning_effort: low"), encoding="utf-8")
    accepted = invoke("check", "--config", str(config))
    sent = FakeModels.bodies[-1]
    config.write_text(config_text(port, store, f", reasoning_effort: {UNOFFERED}"), "utf-8")
    declined = invoke("check", "--config", str(config))

    assert openai["reasoning_effort"] == "low"
    assert openai["temperature"] == 0.0
    assert anthropic.request(ASKED, "m", "k").body["output_config"] == {"effort": "low"}
    assert anthropic.request(ASKED, "m", "k").body["thinking"] == {
        "type": "enabled",
        "budget_tokens": 2048,
    }
    assert google.config("s") == {
        "system_instruction": "s",
        "temperature": 0.0,
        "thinking_config": {"thinking_level": "LOW", "thinking_budget": 2048},
    }
    assert bedrock.converse(ASKED, "m")["inferenceConfig"] == {"temperature": 0.0}
    assert bedrock.converse(ASKED, "m")["additionalModelRequestFields"] == {
        "reasoning_effort": "low"
    }
    assert (azure["reasoning_effort"], azure["temperature"]) == ("low", 0.0)
    assert "takes no temperature" in str(refused.value)
    assert "reasoning_effort, thinking_budget, max_tokens" in str(refused.value)
    assert accepted.exit_code == 0, accepted.output
    assert sent["output_config"] == {"effort": "low"}
    assert "anthropic model-a answered, accepting reasoning_effort=low, max_tokens=2048" in (
        accepted.output
    )
    assert declined.exit_code == 1
    assert f"refused the call with reasoning_effort={UNOFFERED}, max_tokens=2048" in (
        declined.output
    )
    assert "not supported by this model" in declined.output


def test_agreement_measured_per_setting(workspace):
    tmp_path = workspace[0]

    low = invoke("extract", "--sample", "5", "--set", "reasoning_effort=low", "--out", "low")
    efforts = {(b.get("output_config") or {}).get("effort") for b in FakeModels.bodies}
    default = invoke("extract", "--sample", "5", "--out", "default")
    compared = invoke("compare", "low", "default")

    assert low.exit_code == 0, low.output
    assert default.exit_code == 0, default.output
    assert efforts == {"low"}
    reports = [
        json.loads((tmp_path / f / "extraction.json").read_text()) for f in ("low", "default")
    ]
    assert [m["settings"] for m in reports[0]["models"]] == [
        {"reasoning_effort": "low", "max_tokens": 2048}
    ] * 2
    assert [m["settings"] for m in reports[1]["models"]] == [{"max_tokens": 2048}] * 2
    for report in reports:
        assert report["read"] == 5
        assert set(report["fields"]) == {"outcome", "statutes", "precedents", "facts"}
        assert len(report["seconds"]["per_decision"]) == 5
        # 10 calls of 100 input and 40 output tokens, at $1 and $4 a million.
        assert report["cost"] == pytest.approx(10 * (100 * 1.0 + 40 * 4.0) / 1_000_000)
    assert compared.exit_code == 0, compared.output
    assert "model-a: reasoning_effort=low, max_tokens=2048" in compared.output
    assert "model-a: max_tokens=2048;" in compared.output
    outcome = next(line for line in compared.output.splitlines() if "outcome agreement" in line)
    rate = reports[0]["fields"]["outcome"]
    assert f"{rate['agreed']}/5 ({rate['rate']:.0%})" in outcome
    assert "$0.001 a decision" in compared.output


def test_cost_stated_before_spending(workspace):
    planned = invoke("extract", "--sample", "5", "--dry-run")

    assert planned.exit_code == 0, planned.output
    assert "5 decisions, 10 model calls" in planned.output
    assert "input: unknown until decisions are fetched" in planned.output
    # At most 10 calls of 2,048 output tokens at $4 a million.
    assert "cost, an estimate: from $0.00 (input alone) to $0.08" in planned.output
    assert "nothing was sent" in planned.output
    assert FakeModels.bodies == []


def test_progress_without_a_terminal(workspace, tmp_path: Path):
    extracted = invoke("extract", "--sample", "3")
    suite = frozen(mixed(3), tmp_path / "suite")
    ran = invoke(
        "run",
        "--suite",
        str(suite),
        "--python",
        f"{AGENTS}:upheld",
        "--runs-dir",
        str(tmp_path / "runs"),
        "--no-capture",
        "--config",
        str(tmp_path / "no-config.yaml"),
    )

    assert extracted.exit_code == 0, extracted.output
    read = [line for line in extracted.output.splitlines() if line.startswith("read ")]
    assert len(read) == 3
    assert read[-1].startswith("read 3/3 ")
    assert read[-1].endswith("$0.00 so far")  # 6 calls cost $0.0016
    assert ran.exit_code == 0, ran.output
    lines = ran.output.splitlines()
    assert sum(line.startswith("answered ") for line in lines) == 3
    assert sum(line.startswith("scored ") for line in lines) == 3
    assert any(line.startswith("scored 3/3 case-") for line in lines)
