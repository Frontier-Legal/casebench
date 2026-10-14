"""A lawyer writes one test case on a topic of their choice in a few minutes (decision 0039)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

import pytest
import yaml
from click.testing import CliRunner

from casebench.cases.draft import DRAFT
from casebench.cli import main
from casebench.core.case import Approval, ReferenceSource
from casebench.suites.freeze import load
from tests.corpus.document_api import KEY, start_document_api
from tests.judge.fake_judge import start_fake_judge
from tests.metrics.authorities import start_resolving_judge, write_corpus
from tests.report.suites import frozen, mixed

AGENTS = Path(__file__).parents[1] / "report" / "agents.py"
# What the drafting model reads in decision 102 of the test document API.
DRAFTED = {
    "question": "Is severance pay owed to the worker?",
    "facts": "The worker claims severance pay after twenty years of service.",
    "outcome": {"label": "upheld", "quote": "HÜKÜM: Onanmasına."},
    "statutes": [{"citation": "1475 sayılı Kanun m. 14", "quote": "Kıdem tazminatı."}],
    "precedents": [],
}


class Drafter(BaseHTTPRequestHandler):
    """A model behind the Messages API that drafts decision 102's case, and counts its calls."""

    asked: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Drafter.asked.append(body["system"])
        text = json.dumps(DRAFTED, ensure_ascii=False)
        payload = json.dumps(
            {
                "content": [{"type": "text", "text": text}],
                "usage": {"input_tokens": 1000, "output_tokens": 500},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


@pytest.fixture
def described(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A licensed document API whose results carry citations, and a priced drafting model."""
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    documents = start_document_api()
    Drafter.asked = []
    model = ThreadingHTTPServer(("127.0.0.1", 0), Drafter)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    drafter = {
        "provider": "anthropic",
        "model": "drafter",
        "options": {"base_url": f"http://127.0.0.1:{model.server_port}", "max_tokens": 4096},
        "price": {"input": 3.0, "output": 15.0},
    }
    config = {
        "corpus": {
            "connector": "http",
            "jurisdictions": ["TR"],
            "options": {
                "base_url": f"http://127.0.0.1:{documents.server_port}/v1",
                "headers": {"Authorization": "Bearer ${DOC_KEY}"},
                "search_path": "/search",
                "fetch_path": "/documents/{id}",
                "search_results": "$.results[*]",
                "result_fields": {"id": "$.work.work_id", "citation": "$.citation"},
                "fields": {
                    "id": "$.work_id",
                    "jurisdiction": "$.jurisdiction.code",
                    "court": "$.issuers[0].name",
                    "date": "$.dates[1].date",
                    "text": "$.expressions[0].text",
                },
            },
        },
        "extract": {"models": [drafter, {**drafter, "model": "second"}]},
    }
    (tmp_path / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    yield tmp_path
    documents.shutdown()
    model.shutdown()


def new_case(suite: Path, typed: list[str], *flags: str):
    return CliRunner().invoke(
        main, ["case", "new", "--suite", str(suite), *flags], input="\n".join(typed) + "\n"
    )


def test_from_a_topic_to_a_saved_case(described: Path):
    suite = described / "severance"
    # Topic, the first decision, then: keep the question, facts and outcome, add a statute,
    # keep no precedents, name the reviewer, and confirm.
    typed = ["kıdem tazminatı", "1", "", "", "", "1475 sayılı Kanun m. 14; 4857 sayılı Kanun m. 2"]
    typed += ["", "Av. Deniz Kaya", "y"]

    made = new_case(suite, typed)

    assert made.exit_code == 0, made.output
    assert "1. Yargıtay 22. Hukuk Dairesi, E. 2022/77 K. 2023/90, 02.05.2024" in made.output
    assert Drafter.asked == [DRAFT]  # one model call
    _, [case] = load(suite)
    assert case.approval is Approval.APPROVED
    assert case.reference.author == "Av. Deniz Kaya"
    assert case.reference.source is ReferenceSource.COURT
    assert case.provenance is not None
    assert case.provenance.source_decision_id == "corpus:102"
    assert case.task.inputs["question"] == DRAFTED["question"]
    facts = {f.value: f.evidence for f in case.reference.facts}
    assert facts["upheld"].quote == "HÜKÜM: Onanmasına."
    assert facts["1475 sayılı Kanun m. 14"].quote == "Kıdem tazminatı."  # kept as drafted
    assert facts["4857 sayılı Kanun m. 2"].note == "written by Av. Deniz Kaya"  # added
    assert len(case.reference.criteria) == 3
    assert case.metrics == ["criteria"]


def test_written_by_hand(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    suite = tmp_path / "notice"
    typed = ["Is the dismissal valid without a written notice?", "No, the notice must be written."]
    typed += ["4857 sayılı İş Kanunu m. 18", "", "Av. Deniz Kaya", "y"]

    written = new_case(suite, typed, "--manual")
    judge = start_resolving_judge()
    store = write_corpus(tmp_path / "store")
    options = f"{{base_url: 'http://127.0.0.1:{judge.server_port}', max_tokens: 1024}}"
    (tmp_path / "casebench.yaml").write_text(
        f"judge: {{provider: anthropic, model: judge, options: {options}}}\n"
        f"corpus: {{connector: folder, options: {{path: '{store.as_posix()}'}}}}\n",
        encoding="utf-8",
    )
    try:
        resolved = CliRunner().invoke(main, ["case", "resolve", "--suite", str(suite)])
    finally:
        judge.shutdown()

    assert written.exit_code == 0, written.output
    assert "not in the corpus yet: 4857 sayılı İş Kanunu m. 18" in written.output
    assert resolved.exit_code == 0, resolved.output
    assert "1 citations resolved in 1 cases" in resolved.output
    _, [case] = load(suite)
    assert case.reference.source is ReferenceSource.LAWYER
    assert case.approval is Approval.APPROVED
    statute = next(f for f in case.reference.facts if f.kind == "statute")
    assert statute.document_id == "corpus:law-4857-18"
    assert case.metrics == ["criteria", "statute", "citation_integrity"]


def test_time_and_cost_shown(described: Path):
    typed = ["kıdem tazminatı", "1", "", "", "", "", "", "Av. Deniz Kaya", "y"]

    made = new_case(described / "severance", typed)

    assert made.exit_code == 0, made.output
    # 1,000 input and 500 output tokens at $3 and $15 a million.
    drafted = next(line for line in made.output.splitlines() if line.startswith("drafted by"))
    assert drafted.startswith("drafted by anthropic/drafter in ")
    assert drafted.endswith("s, 1500 tokens, $0.011")


def test_the_suite_changes_visibly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    suite = frozen(mixed(1), tmp_path / "suite")
    recorded, _ = load(suite)
    judge = start_fake_judge()
    options = f"{{base_url: 'http://127.0.0.1:{judge.server_port}', max_tokens: 1024}}"
    (tmp_path / "casebench.yaml").write_text(
        f"judge: {{provider: anthropic, model: judge, options: {options}}}\n", encoding="utf-8"
    )
    typed = ["How did the court rule?", "upheld", "", "", "Av. Deniz Kaya", "y"]
    try:
        added = new_case(suite, typed, "--manual")
        now, _ = load(suite)
        ran = CliRunner().invoke(
            main,
            ["run", "--suite", str(suite), "--python", f"{AGENTS}:upheld", "--no-capture"],
        )
    finally:
        judge.shutdown()

    assert added.exit_code == 0, added.output
    assert now.content_hash != recorded.content_hash
    assert f"suite outcomes: {recorded.content_hash} -> {now.content_hash}" in added.output
    assert now.case_count == 2
    assert ran.exit_code == 0, ran.output
    assert f"suite outcomes at {now.content_hash}" in ran.output
    [run] = (tmp_path / ".casebench" / "runs").iterdir()
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    assert report["suite_hash"] == now.content_hash
