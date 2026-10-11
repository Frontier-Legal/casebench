"""Where the right authority was lost: each court authority followed through the steps."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.capture.read import ids_in
from casebench.cli import main
from casebench.core.case import Case, Evidence, Fact, Reference, ReferenceSource, Task
from casebench.suites.freeze import freeze
from tests.metrics.authorities import start_resolving_judge, write_corpus
from tests.report.funnel_upstream import start_funnel_upstream

AGENT = Path(__file__).parent / "funnel_agent.py"
OUTCOME_AGENT = Path(__file__).parent / "agents.py"


def authority(kind: str, document_id: str) -> Fact:
    return Fact(
        id=document_id,
        kind=kind,
        value=document_id,
        evidence=Evidence(doc="tr-1"),
        document_id=document_id,
    )


def case(facts: list[Fact], task: str, metrics: list[str]) -> Case:
    return Case(
        id="c1",
        task=Task.model_validate(
            {"type": task, "question": "Which decisions decide this?", "facts": "Dismissed."}
        ),
        reference=Reference(source=ReferenceSource.COURT, facts=facts),
        metrics=metrics,
    )


@pytest.fixture
def traced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    upstream, judge = start_funnel_upstream(), start_resolving_judge()
    base = f"http://127.0.0.1:{upstream.server_port}"
    config = {
        "target": {"type": "command", "run": f"{sys.executable} {AGENT} {{question}}"},
        "corpus": {
            "connector": "folder",
            "options": {"path": str(write_corpus(tmp_path / "corpus"))},
        },
        "judge": {
            "provider": "anthropic",
            "model": "judge-model",
            "options": {"base_url": f"http://127.0.0.1:{judge.server_port}", "max_tokens": 256},
        },
        "capture": {
            "routes": [
                {"name": "anthropic", "upstream": base},
                {
                    "name": "search",
                    "upstream": base,
                    "env": "SEARCH_URL",
                    "doc_ids": "$.result[*].id",
                },
                {
                    "name": "rerank",
                    "upstream": base,
                    "env": "RERANK_URL",
                    "step": "rerank",
                    "doc_ids": "$.results[*].id",
                    "doc_ids_in": "$.documents[*]",
                },
            ]
        },
    }
    (tmp_path / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    yield tmp_path
    upstream.shutdown()
    judge.shutdown()


def run(*extra: str):
    return CliRunner().invoke(main, ["run", "--suite", "suite", "--run-id", "r", *extra])


def report(folder: Path) -> dict:
    return json.loads((folder / ".casebench" / "runs" / "r" / "report.json").read_text("utf-8"))


def test_rerank_drop(traced: Path):
    gold = [authority("precedent", "dec-9hd-2019-1"), authority("precedent", "law-4857-18")]
    freeze("funnel", [case(gold, "precedent", ["precedent"])], traced / "suite")

    ran = run()

    assert ran.exit_code == 0, ran.output
    [funnel] = report(traced)["funnel"]["cases"]
    labels = {a["document_id"]: a["label"] for a in funnel["authorities"]}
    assert labels == {"dec-9hd-2019-1": None, "law-4857-18": "rerank_drop"}
    assert "authority funnel: 2 court authorities in 1 cases" in ran.output
    for line in ("retrieved      2   100%", "kept           1    50%", "read           1    50%"):
        assert line in ran.output
    assert "cited          1    50%" in ran.output
    assert "rerank_drop 1" in ran.output


def test_citation_from_memory(traced: Path):
    gold = [authority("precedent", "dec-9hd-2019-1")]
    freeze("funnel", [case(gold, "precedent", ["precedent"])], traced / "suite")

    ran = run()

    assert ran.exit_code == 0, ran.output
    [funnel] = report(traced)["funnel"]["cases"]
    assert funnel["ungrounded"] == ["TBK m. 49"]  # law-6098-49: in the corpus, never retrieved
    assert "ungrounded citations: 1" in ran.output


def test_a_black_box_still_gets_a_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    ruling = Fact(id="o", kind="outcome", value="reversed", evidence=Evidence(doc="tr-1"))
    facts = [ruling, authority("precedent", "dec-9hd-2019-1")]
    freeze("black-box", [case(facts, "outcome", ["outcome"])], tmp_path / "suite")

    ran = CliRunner().invoke(
        main,
        ["run", "--suite", "suite", "--python", f"{OUTCOME_AGENT}:upheld", "--run-id", "r"],
    )

    assert ran.exit_code == 0, ran.output
    assert "outcome · outcome" in ran.output
    assert "authority funnel: no diagnostic possible" in ran.output
    [funnel] = report(tmp_path)["funnel"]["cases"]
    assert (funnel["diagnostic"], funnel["authorities"]) == (False, [])


def test_read_finds_ids_as_whole_words():
    body = {"messages": [{"content": "See [tr-12] and the 2012 ruling; 12 more."}]}

    assert ids_in(body, {"tr-12", "12", "tr-1", "2012"}) == ["12", "2012", "tr-12"]
    assert ids_in(body, {"tr-1"}) == []
