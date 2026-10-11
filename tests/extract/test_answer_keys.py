"""Answer keys written by the court."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import ConfigError, load_config
from casebench.extract.run import read_keys
from casebench.suites.freeze import load
from tests.extract.decisions import DECISIONS
from tests.extract.fake_models import start_fake_models


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def models_config(port: int, second: str = "model-b") -> str:
    options = f"{{base_url: 'http://127.0.0.1:{port}', max_tokens: 2048}}"
    return (
        "extract:\n  models:\n"
        f"    - {{provider: anthropic, model: model-a, options: {options}}}\n"
        f"    - {{provider: anthropic, model: {second}, options: {options}}}\n"
    )


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    store = tmp_path / "decisions"
    store.mkdir()
    for decision_id, (country, court, level, day, text) in DECISIONS.items():
        (store / f"{decision_id}.json").write_text(
            json.dumps(
                {
                    "id": decision_id,
                    "jurisdiction": country,
                    "court": court,
                    "level": level,
                    "date": day,
                    "text": text,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    server = start_fake_models()
    config = tmp_path / "casebench.yaml"
    config.write_text(
        f"corpus: {{connector: folder, options: {{path: '{store.as_posix()}'}}}}\n"
        + models_config(server.server_port),
        encoding="utf-8",
    )
    yield tmp_path, config, server.server_port
    server.shutdown()


def extract(config: Path, out: Path):
    return invoke("extract", "--sample", "6", "--config", str(config), "--out", str(out))


def test_only_agreed_extractions_become_drafts(workspace):
    tmp_path, config, _ = workspace

    ran = extract(config, tmp_path / "keys")

    assert ran.exit_code == 0, ran.output
    assert "6 decisions read, 5 answer keys kept" in ran.output
    for line in (
        "outcome     agreement 0.83",
        "statutes    agreement 0.83",
        "precedents  agreement 1.00",
        "facts       agreement 0.83",
    ):
        assert line in ran.output
    keys = {k.decision_id: {f.kind for f in k.facts} for k in read_keys(tmp_path / "keys")}
    assert keys["tr-2"] == {"statute", "precedent"}  # the models read its outcome differently
    assert keys["en-1"] == {"outcome", "precedent"}  # model B listed an extra statute
    assert "en-2" not in keys  # its facts gave the ruling away
    report = json.loads((tmp_path / "keys" / "extraction.json").read_text(encoding="utf-8"))
    assert [m["model"] for m in report["models"]] == ["model-a", "model-b"]
    assert all(m["input_tokens"] == 600 for m in report["models"])

    same = tmp_path / "same.yaml"
    same.write_text(
        config.read_text(encoding="utf-8").replace("model-b", "model-a"), encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="two different models"):
        load_config(same)


def test_each_fact_points_at_its_passage(workspace):
    tmp_path, config, _ = workspace
    extract(config, tmp_path / "keys")

    for key in read_keys(tmp_path / "keys"):
        text = DECISIONS[key.decision_id][4]
        for fact in key.facts:
            assert fact.evidence.span is not None
            start, end = fact.evidence.span
            assert text[start:end] == fact.evidence.quote


def test_date_filter(workspace):
    tmp_path, config, _ = workspace
    extract(config, tmp_path / "keys")

    made = invoke(
        "generate",
        "--keys",
        str(tmp_path / "keys"),
        "--types",
        "statute",
        "--n",
        "10",
        "--after",
        "2024-12-31",
        "--suite-id",
        "fresh",
        "--out",
        str(tmp_path / "suite"),
    )

    assert made.exit_code == 0, made.output
    assert "cutoff 2024-12-31: 2 decisions allowed, 3 excluded" in made.output
    manifest, cases = load(tmp_path / "suite")
    assert {c.provenance.source_decision_id for c in cases if c.provenance} == {"tr-2", "de-1"}
    assert manifest.generation["after"] == "2024-12-31"
    assert manifest.generation["decisions_allowed"] == 2


def test_stratified_suite(workspace):
    tmp_path, config, _ = workspace
    extract(config, tmp_path / "keys")

    made = invoke(
        "generate",
        "--keys",
        str(tmp_path / "keys"),
        "--types",
        "outcome",
        "--n",
        "3",
        "--stratify",
        "court",
        "--suite-id",
        "balanced",
        "--out",
        str(tmp_path / "suite"),
    )

    assert made.exit_code == 0, made.output
    _, cases = load(tmp_path / "suite")
    sources = [c.provenance.source_decision_id for c in cases if c.provenance]
    levels = sorted(DECISIONS[source][2] for source in sources if source)
    assert levels == ["appellate", "first_instance", "supreme"]


def test_facts_never_give_the_ruling_away(workspace):
    tmp_path, config, _ = workspace
    extract(config, tmp_path / "keys")
    invoke(
        "generate",
        "--keys",
        str(tmp_path / "keys"),
        "--types",
        "outcome",
        "--n",
        "10",
        "--suite-id",
        "outcomes",
        "--out",
        str(tmp_path / "suite"),
    )

    _, cases = load(tmp_path / "suite")

    assert cases
    for case in cases:
        [outcome] = case.reference.facts
        facts = case.task.inputs["facts"]
        assert outcome.evidence.quote is not None
        assert outcome.evidence.quote.casefold() not in facts.casefold()
        assert outcome.value not in facts.casefold()
        assert "Answer with exactly one of" in case.task.inputs["question"]
