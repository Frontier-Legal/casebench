"""Setup spends one search and one document, and greets the agent once (decision 0045)."""

import os
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench import keys
from casebench.cli import main
from tests.corpus.document_api import CITED_AS, KEY, DocumentApi, start_document_api

FIELDS = {
    "id": "$.work_id",
    "jurisdiction": "$.jurisdiction.code",
    "court": "$.issuers[0].name",
    "date": "$.dates[1].date",
    "text": "$.expressions[0].text",
}
AGENT = f'''\
"""An agent that answers, and writes down each question it is asked."""

from pathlib import Path


def answer(question):
    asked = Path(__file__).with_name("asked.txt")
    asked.write_text(asked.read_text() + question + "\\n" if asked.exists() else question + "\\n")
    return "The court reversed the judgment: the dismissal is invalid ({CITED_AS["101"]})."
'''


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


def test_check_greets_the_agent_once(project: Path):
    api = start_document_api()
    (project / "agent.py").write_text(AGENT, encoding="utf-8")
    config = {
        "target": {"type": "python", "entry": "agent.py:answer"},
        "corpus": corpus(api.server_port),
    }
    (project / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    try:
        checked = invoke("check")
    finally:
        api.shutdown()

    assert checked.exit_code == 0, checked.output
    assert "target   passed: answered" in checked.output
    # One short message, which asks the agent for no research, and nothing else.
    assert (project / "asked.txt").read_text(encoding="utf-8") == "Hi. How are you?\n"


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
