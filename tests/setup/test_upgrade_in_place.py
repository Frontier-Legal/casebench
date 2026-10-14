"""An existing setup upgrades in place: update casebench.yaml, read old files, keep caches
(decision 0042)."""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.core.case import Case, Evidence, Fact, Provenance, Reference, ReferenceSource, Task
from casebench.core.score import Direction, Score, ScoreKind
from casebench.corpus.binding import CorpusConfig
from casebench.corpus.corpora import Corpora
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.suites.freeze import MANIFEST_FILE, freeze, load
from tests.corpus.document_api import KEY, DocumentApi, start_document_api
from tests.corpus.profiles import http_options
from tests.judge.fake_judge import start_fake_judge
from tests.metrics.authorities import start_resolving_judge, write_corpus
from tests.setup.test_init_reads_the_code import AGENT

CATALOG = {
    "anthropic": {
        "name": "Anthropic",
        "npm": "@ai-sdk/anthropic",
        "env": ["ANTHROPIC_API_KEY"],
        "models": {
            "judge-model": {
                "family": "claude",
                "cost": {"input": 3.0, "output": 15.0},
                "limit": {"context": 200000, "output": 64000},
            }
        },
    }
}


def invoke(*args: str, typed: str = ""):
    return CliRunner().invoke(main, list(args), input=typed)


def test_init_updates_an_existing_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    (tmp_path / "catalog.json").write_text(json.dumps(CATALOG), encoding="utf-8")
    before = {
        "target": {"type": "python", "entry": "agent.py:answer", "max_concurrency": 2},
        "judge": {"provider": "anthropic", "model": "judge-model", "options": {"max_tokens": 1024}},
        "capture": {"functions": [{"function": "agent.py:search", "step": "retrieval"}]},
    }
    (tmp_path / "casebench.yaml").write_text(
        "# written by an earlier casebench\n" + yaml.safe_dump(before), encoding="utf-8"
    )

    updated = invoke("init", "--catalog", "catalog.json", typed="y\n")
    again = invoke("init", "--catalog", "catalog.json")

    assert updated.exit_code == 0, updated.output
    assert "add judge judge-model: price $3.0 and $15.0 a million" in updated.output
    assert "add judge judge-model: context window of 200000 tokens" in updated.output
    assert "add openai.OpenAI at agent.py:6: route api-fireworks-ai" in updated.output
    after = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    assert after["target"] == before["target"]  # every setting already there stays
    assert after["capture"]["functions"] == before["capture"]["functions"]
    assert after["judge"] == {
        **before["judge"],
        "price": {"input": 3.0, "output": 15.0},
        "context_window": 200000,
    }
    assert [route["name"] for route in after["capture"]["routes"]] == ["api-fireworks-ai"]
    assert again.exit_code == 0, again.output
    assert "has everything this version adds; nothing to change" in again.output


def old_suite(folder: Path) -> Path:
    """A suite as frozen before formats and before ids named their corpus."""
    case = Case(
        id="tr-1:statute",
        task=Task.model_validate({"type": "statute", "question": "Which statute decides it?"}),
        reference=Reference(
            source=ReferenceSource.COURT,
            facts=[
                Fact(
                    id="statute-1",
                    kind="statute",
                    value="İş K. md. 18",
                    evidence=Evidence(doc="dec-9hd-2019-1"),
                    document_id="law-4857-18",
                )
            ],
        ),
        metrics=["statute"],
        provenance=Provenance(builder="court", source_decision_id="dec-9hd-2019-1"),
    )
    freeze("old", [case], folder)
    manifest = json.loads((folder / MANIFEST_FILE).read_text(encoding="utf-8"))
    for name in ("format", "case_format", "corpora", "jurisdictions"):
        manifest.pop(name, None)
    (folder / MANIFEST_FILE).write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def test_old_files_are_read_as_they_are(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    suite = old_suite(tmp_path / "suite")
    with pytest.warns(UserWarning, match="frozen before suites named their format"):
        manifest, _ = load(suite)
    log = RunLog.create(
        tmp_path / ".casebench" / "runs" / "first",
        RunInfo(run_id="first", suite_id="old", suite_hash=manifest.content_hash, target="python"),
    )
    log.append(Result(case_id="tr-1:statute", output="4857 sayılı İş Kanunu m. 18 applies."))
    headerless = log.folder / "scores" / "20261012T000000Z-old.jsonl"
    headerless.parent.mkdir()
    score = Score(
        case_id="tr-1:statute",
        metric="statute",
        metric_version="1",
        kind=ScoreKind.LLM,
        direction=Direction.HIGHER,
        value=0.0,
        task_type="statute",
        reference_source=ReferenceSource.COURT,
        approval="draft",  # type: ignore[arg-type]
    )
    headerless.write_text(score.model_dump_json() + "\n", encoding="utf-8")
    judge = start_resolving_judge()
    store = write_corpus(tmp_path / "store")
    options = f"{{base_url: 'http://127.0.0.1:{judge.server_port}', max_tokens: 1024}}"
    (tmp_path / "casebench.yaml").write_text(
        "target: {type: python, entry: agent.py:answer}\n"
        f"judge: {{provider: anthropic, model: judge, options: {options}}}\n"
        f"corpus: {{connector: folder, options: {{path: '{store.as_posix()}'}}}}\n",
        encoding="utf-8",
    )
    try:
        with pytest.warns(UserWarning, match="read as casebench.suite/1.0"):
            ran = invoke("run", "--suite", str(suite), "--run-id", "first", "--no-capture")
    finally:
        judge.shutdown()

    assert ran.exit_code == 0, ran.output
    assert "0 cases sent, 1 stored" in ran.output
    [old] = RunLog.read_scores(headerless)  # the first and only score of an old set is kept
    assert old.value == 0.0
    [now] = RunLog.read_scores(log.score_sets()[-1])
    # The court's unqualified id is read as the one corpus's, so the answer's matches it.
    assert (now.metric, now.value, now.label) == ("statute", 1.0, "correct")


def test_caches_carry_over(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOC_KEY", KEY)
    server = start_document_api()
    base = f"http://127.0.0.1:{server.server_port}/v1"
    plain = http_options(base)
    described = {
        **plain,
        "search_results": "$.results[*]",
        "result_fields": {"id": "$.work.work_id", "citation": "$.citation"},
    }
    try:
        before = Corpora({"tr": CorpusConfig(connector="http", options=plain)}, tmp_path / "c")
        before.raw("tr:101")
        after = Corpora({"tr": CorpusConfig(connector="http", options=described)}, tmp_path / "c")
        document = after.raw("tr:101")
    finally:
        server.shutdown()

    assert document["id"] == "101"
    assert DocumentApi.fetches == {"101": 1}  # fetched once, before the results were mapped


def test_check_says_what_is_out_of_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    documents, judge = start_document_api(), start_fake_judge()
    config = {
        "corpus": {
            "connector": "http",
            "options": http_options(f"http://127.0.0.1:{documents.server_port}/v1"),
        },
        "judge": {
            "provider": "anthropic",
            "model": "judge-model",
            "options": {"base_url": f"http://127.0.0.1:{judge.server_port}", "max_tokens": 1024},
        },
    }
    (tmp_path / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    try:
        checked = invoke("check", "--query", "feshi")
    finally:
        documents.shutdown()
        judge.shutdown()

    assert checked.exit_code == 0, checked.output  # advice never fails the check
    assert "could use corpus corpus: its search results are not described" in checked.output
    assert "`casebench corpus add` suggests where its results keep" in checked.output
    assert "could use judge: no price, so costs show as tokens; `casebench init`" in (
        checked.output
    )
    assert "could use judge: no context window" in checked.output
