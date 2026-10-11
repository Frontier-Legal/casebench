"""Statute and precedent scores compare corpus documents; judge replies stay with the run."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.core.case import Evidence, Fact
from casebench.references.court import AnswerKey
from casebench.runs.log import RunLog
from casebench.suites.freeze import load
from tests.metrics.authorities import ResolvingJudge, start_resolving_judge, write_corpus

AGENT = Path(__file__).parent / "agents.py"


def fact(number: int, kind: str, written: str) -> Fact:
    return Fact(id=f"{kind}-{number}", kind=kind, value=written, evidence=Evidence(doc="tr-1"))


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_resolving_judge()
    corpus = write_corpus(tmp_path / "corpus")
    options = f"{{base_url: 'http://127.0.0.1:{server.server_port}', max_tokens: 1024}}"
    config = tmp_path / "casebench.yaml"
    config.write_text(
        f"judge: {{provider: anthropic, model: judge-model, options: {options}}}\n"
        f"corpus: {{connector: folder, options: {{path: '{corpus.as_posix()}'}}}}\n",
        encoding="utf-8",
    )
    key = AnswerKey(
        decision_id="tr-1",
        jurisdiction="TR",
        inputs={"facts": "The worker was dismissed without a reason."},
        facts=[
            fact(1, "statute", "4857 sayılı İş Kanunu m. 18"),
            fact(2, "statute", "1475 sayılı Kanun m. 14"),
            fact(3, "statute", "5510 sayılı Kanun m. 99"),
            fact(4, "precedent", "Yargıtay 9. HD E. 2019/1 K. 2020/2"),
        ],
    )
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / "keys.jsonl").write_text(key.model_dump_json() + "\n", encoding="utf-8")
    yield tmp_path, config
    server.shutdown()


def generate(tmp_path: Path, config: Path):
    return CliRunner().invoke(
        main,
        [
            "generate",
            "--keys",
            str(tmp_path / "keys"),
            "--types",
            "statute,precedent",
            "--n",
            "10",
            "--suite-id",
            "authorities",
            "--out",
            str(tmp_path / "suite"),
            "--config",
            str(config),
        ],
    )


def run(tmp_path: Path, config: Path):
    return CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(tmp_path / "suite"),
            "--config",
            str(config),
            "--python",
            f"{AGENT}:cites",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--run-id",
            "r",
            "--no-capture",
        ],
    )


def scores(tmp_path: Path) -> dict[str, dict]:
    report = json.loads((tmp_path / "runs" / "r" / "report.json").read_text("utf-8"))
    return {s["metric"]: s for s in report["scores"]}


def test_statutes_and_precedents_scored_by_corpus_document(workspace):
    tmp_path, config = workspace

    made = generate(tmp_path, config)
    ran = run(tmp_path, config)

    assert made.exit_code == 0, made.output
    assert "statute: 2 court citations found in the corpus, 1 not found and dropped" in made.output
    assert "precedent: 1 court citations found in the corpus, 0 not found" in made.output
    manifest, cases = load(tmp_path / "suite")
    assert manifest.generation["citations"]["statute"] == {"resolved": 2, "dropped": 1}
    statute_case = next(c for c in cases if c.task.type == "statute")
    assert [f.document_id for f in statute_case.reference.facts] == ["law-4857-18", "law-1475-14"]

    assert ran.exit_code == 0, ran.output
    by_metric = scores(tmp_path)
    statute = by_metric["statute"]
    assert statute["label"] == "missed statute, wrong statute"
    assert statute["value"] == pytest.approx(0.5)  # 4857 m. 18 right; 1475 missed; TBK 49 wrong
    assert "precision 0.50, recall 0.50" in statute["explanation"]
    precedent = by_metric["precedent"]
    assert (precedent["value"], precedent["label"]) == (1.0, "correct")  # the statute is ignored


def test_rescoring_reuses_the_judges_replies(workspace):
    tmp_path, config = workspace
    generate(tmp_path, config)
    run(tmp_path, config)
    calls = len(ResolvingJudge.calls)
    first = scores(tmp_path)

    again = run(tmp_path, config)

    assert again.exit_code == 0, again.output
    assert "0 cases sent, 2 stored" in again.output
    assert len(ResolvingJudge.calls) == calls
    assert scores(tmp_path) == first
    assert len(RunLog(tmp_path / "runs" / "r").score_sets()) == 2


def test_judge_family_warning(workspace):
    tmp_path, config = workspace
    generate(tmp_path, config)

    ran = run(tmp_path, config)

    assert ran.exit_code == 0, ran.output
    assert "pick a judge from another model family than your target's model" in ran.stderr


def test_statute_cases_need_a_judge_and_a_corpus(workspace):
    tmp_path, _ = workspace
    bare = tmp_path / "bare.yaml"
    bare.write_text("{}\n", encoding="utf-8")

    made = generate(tmp_path, bare)

    assert made.exit_code != 0
    assert "need `judge:` and `corpus:` in the config" in made.output
