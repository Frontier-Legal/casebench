"""Setup spends one search and one fetch, and ends with a one-case demo from the user's own
corpus (decision 0045)."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

import pytest
import yaml
from click.testing import CliRunner

from casebench import keys
from casebench.cases.draft import DRAFT
from casebench.cli import main
from casebench.judge import prompts
from tests.corpus.document_api import CITED_AS, KEY, DocumentApi, start_document_api

FIELDS = {
    "id": "$.work_id",
    "jurisdiction": "$.jurisdiction.code",
    "court": "$.issuers[0].name",
    "date": "$.dates[1].date",
    "text": "$.expressions[0].text",
}
# What a drafting model reads in decision 101 of the test document API, quoting its text.
DRAFTED = {
    "question": "Is the worker's dismissal valid?",
    "facts": "The employer dismissed the worker, who challenged the dismissal.",
    "outcome": {"label": "reversed", "quote": "HÜKÜM: Bozulmasına."},
    "statutes": [],
    "precedents": [],
}
AGENT = f'''\
"""An agent that answers, citing the decision, and counts the questions it is asked."""

from pathlib import Path


def answer(question):
    asked = Path(__file__).with_name("asked.txt")
    asked.write_text(asked.read_text() + question + "\\n" if asked.exists() else question + "\\n")
    return "The court reversed the judgment: the dismissal is invalid ({CITED_AS["101"]})."
'''


class Model(BaseHTTPRequestHandler):
    """A model behind the Messages API that drafts decision 101's case and grades an answer
    by whether it has each criterion's words; it counts what it is asked."""

    asked: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        system, user = body["system"], body["messages"][0]["content"]
        if system == DRAFT:
            Model.asked.append("draft")
            reply: object = DRAFTED
        elif system == prompts.GRADE:
            Model.asked.append("grade")
            answer, criteria = user.split("Answer:\n", 1)[1].split("\n\nCriteria:\n", 1)
            reply = [
                {"id": c["id"], "met": True, "quote": answer.strip()} for c in json.loads(criteria)
            ]
        else:
            raise AssertionError(f"unexpected prompt: {system[:40]}")
        text = json.dumps(reply, ensure_ascii=False)
        payload = json.dumps(
            {"content": [{"type": "text", "text": text}], "usage": {"input_tokens": 1}}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def corpus(port: int, probe: str = "feshi") -> dict:
    return {
        "connector": "http",
        "jurisdictions": ["TR"],
        "probe": probe,
        "options": {
            "base_url": f"http://127.0.0.1:{port}/v1",
            "headers": {"Authorization": "Bearer ${DOC_KEY}"},
            "search_path": "/search",
            "fetch_path": "/documents/{id}",
            "search_results": "$.results[*]",
            "result_fields": {"id": "$.work.work_id", "citation": "$.citation"},
            "fields": FIELDS,
        },
    }


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(keys, "_held", {})
    os.environ["DOC_KEY"] = KEY
    os.environ["ANTHROPIC_API_KEY"] = "a-judge-key"
    DocumentApi.searches, DocumentApi.fetches = [], {}
    Model.asked = []
    return tmp_path


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def test_setup_spends_one_search_and_one_document(project: Path):
    api = start_document_api()
    (project / "casebench.yaml").write_text(
        # A search that finds two decisions, as a real store's finds many.
        yaml.safe_dump({"corpus": corpus(api.server_port, "feshi kıdem")}),
        encoding="utf-8",
    )
    try:
        checked = invoke("check")
    finally:
        api.shutdown()

    assert checked.exit_code == 0, checked.output
    assert DocumentApi.searches == ["feshi kıdem"]
    assert sum(DocumentApi.fetches.values()) == 1  # one of the two it found


def test_the_demo_shows_what_casebench_does(project: Path):
    api = start_document_api()
    model = ThreadingHTTPServer(("127.0.0.1", 0), Model)
    threading.Thread(target=model.serve_forever, daemon=True).start()
    (project / "agent.py").write_text(AGENT, encoding="utf-8")
    judge = {
        "provider": "anthropic",
        "model": "judge-model",
        "options": {"base_url": f"http://127.0.0.1:{model.server_port}", "max_tokens": 1024},
    }
    config = {
        "target": {"type": "python", "entry": "agent.py:answer"},
        "judge": judge,
        "corpus": corpus(api.server_port),
    }
    (project / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    try:
        shown = invoke("demo")
    finally:
        api.shutdown()
        model.shutdown()

    assert shown.exit_code == 0, shown.output
    spends = shown.output.split("This demo spends:\n", 1)[1].splitlines()[:5]
    assert spends == [
        "  1 search of corpus for 'feshi', for 1 result",
        "  1 document fetched",
        "  1 call to anthropic/judge-model to draft the case",
        "  1 turn of your agent",
        "  1 call to anthropic/judge-model to grade the answer",
    ]
    # And no more than it said.
    assert DocumentApi.searches == ["feshi"]
    assert sum(DocumentApi.fetches.values()) == 1
    assert Model.asked == ["draft", "grade"]
    assert (project / "asked.txt").read_text(
        encoding="utf-8"
    ) == "Is the worker's dismissal valid?\n"
    for shown_part in (
        "Is the worker's dismissal valid?",
        "court's outcome",
        "reversed",
        "cites the decision",
        CITED_AS["101"],
        "✓ passed",
        "score 1.00",
    ):
        assert shown_part in shown.output, shown_part
    kept = json.loads((project / ".casebench" / "demo" / "case.json").read_text(encoding="utf-8"))
    assert kept["approval"] == "draft"  # a lawyer approves it, or it is never a reference


def test_a_corpus_name_is_one_casebench_yaml_accepts(project: Path):
    api = start_document_api()
    base = ["corpus", "add", "http", "--base-url", f"http://127.0.0.1:{api.server_port}/v1"]
    flags = [
        "--search-path", "/search", "--fetch-path", "/documents/{id}", "--key-env", "DOC_KEY",
        "--probe", "feshi", "--results", "$.results[*]", "--result-field", "id=$.work.work_id",
        *[part for name, path in FIELDS.items() for part in ("--field", f"{name}={path}")],
        "--yes",
    ]  # fmt: skip
    try:
        refused = invoke(*base, *flags, "--name", "Frontier Legal")
        searched_before = list(DocumentApi.searches)
        added = invoke(*base, *flags, "--name", "frontier-legal")
        checked = invoke("check")
    finally:
        api.shutdown()

    assert refused.exit_code == 2
    assert "use lowercase letters, digits and hyphens, such as frontier-legal" in refused.output
    assert searched_before == []  # refused before anything was searched
    assert added.exit_code == 0, added.output
    assert checked.exit_code == 0, checked.output  # the config it wrote loads
    written = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    assert list(written["corpora"]) == ["frontier-legal"]
