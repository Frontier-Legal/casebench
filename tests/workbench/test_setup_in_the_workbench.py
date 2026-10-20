"""A first-time user sets Casebench up in the workbench: a jurisdiction and its source, a model
tested alone, and a second judge from another family (decision 0065)."""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

from casebench import keys
from casebench.config import load_config
from casebench.workbench.settings import SECTIONS
from tests.corpus.document_api import KEY as DOC_KEY
from tests.corpus.document_api import start_document_api
from tests.corpus.profiles import http_options, profile
from tests.workbench.test_settings import JUDGE, ME, SECOND, project, workbench

DECISION = {
    "id": "cass-soc-2024-03-12",
    "jurisdiction": "FR",
    "court": "Cour de cassation, chambre sociale",
    "date": "2024-03-12",
    "text": "Le licenciement est sans cause réelle et sérieuse.",
}


@pytest.fixture
def fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project with an agent and no casebench.yaml yet, in a process of its own, started in
    the project's folder as init starts the workbench."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(keys, "_held", {})
    (tmp_path / "agent.py").write_text("def answer(question):\n    return 'No.'\n", "utf-8")
    return tmp_path


def test_a_first_visit_is_guided(fresh: Path):
    client = workbench(fresh)
    assert client.get("/api/session").json()["setting_up"] is True

    target = {"type": "python", "entry": "agent.py:answer"}
    saved = client.put("/api/settings/sections/target", json={"value": target}, headers=ME)

    assert saved.status_code == 200
    written = load_config(fresh / "casebench.yaml").target or {}
    assert written["entry"].endswith("agent.py:answer")
    # Once the guide has saved a part, the workbench opens on Home, not on the guide.
    assert client.get("/api/session").json()["setting_up"] is False


def test_a_jurisdiction_is_added_in_a_few_choices(fresh: Path):
    (fresh / "fr").mkdir()
    (fresh / "fr" / "cass-soc.json").write_text(json.dumps(DECISION), encoding="utf-8")
    client = workbench(fresh)
    codes = client.get("/api/setup/jurisdictions", headers=ME).json()
    assert {"FR", "TR", "EU"} <= set(codes)
    assert "UK" not in codes  # written GB, as casebench.yaml reads it

    source = {"connector": "folder", "jurisdictions": ["FR"], "options": {"path": "fr"}}
    tested = client.post(
        "/api/setup/sources/test", json={"block": source, "probe": "licenciement"}, headers=ME
    ).json()
    assert tested["passed"] is True, tested
    saved = client.put("/api/settings/sections/corpora", json={"value": {"fr": source}}, headers=ME)

    assert saved.status_code == 200
    corpus = load_config(fresh / "casebench.yaml").corpora["fr"]
    assert corpus.jurisdictions == ["FR"]


def test_an_empty_source_does_not_pass(fresh: Path):
    (fresh / "empty").mkdir()
    client = workbench(fresh)
    source = {"connector": "folder", "jurisdictions": ["FR"], "options": {"path": "empty"}}

    tested = client.post("/api/setup/sources/test", json={"block": source}, headers=ME).json()

    assert tested["passed"] is False
    assert "no document" in tested["reason"]
    assert "JSON" in tested["next"]


def test_a_document_api_is_connected_without_writing_a_jsonpath(fresh: Path):
    os.environ["DOC_KEY"] = DOC_KEY
    api = start_document_api()
    asked = {
        "base_url": f"http://127.0.0.1:{api.server_port}/v1",
        "search_path": "/search",
        "fetch_path": "/documents/{id}",
        "key_env": "DOC_KEY",
        "probe": "feshi",
        "jurisdictions": ["TR"],
    }
    try:
        client = workbench(fresh)
        searched = client.post("/api/setup/sources/api", json=asked, headers=ME)
        shown = {leaf["path"]: leaf["value"] for leaf in searched.json()["result_choices"]}
        # The person picks each field from the values the search returned.
        picked = {"id": "$.work.work_id", "citation": "$.citation", "passage": "$.highlight"}
        fetched = client.post(
            "/api/setup/sources/api", json={**asked, "result_fields": picked}, headers=ME
        )
    finally:
        api.shutdown()

    assert searched.status_code == 200, searched.text
    assert searched.json()["block"] is None
    assert searched.json()["results"] == "$.results[*]"
    assert shown["$.work.work_id"] == "101"
    assert fetched.status_code == 200, fetched.text
    found = fetched.json()
    block = found["block"]
    assert block["jurisdictions"] == ["TR"]
    assert block["options"]["result_fields"] == picked
    assert found["fields"]["text"] == "$.expressions[0].text"
    assert "court" in found["missing"]
    assert block["options"]["headers"] == {"Authorization": "Bearer ${DOC_KEY}"}
    assert found["name"]
    assert DOC_KEY not in searched.text + fetched.text


def test_an_mcp_server_is_connected_in_the_browser(fresh: Path):
    client = workbench(fresh)
    reached = {"command": f"{sys.executable} -m tests.corpus.mcp_documents"}
    listed = client.post("/api/setup/sources/mcp/tools", json=reached, headers=ME)
    asked = {
        **reached,
        "search_tool": "search",
        "fetch_tool": "get_document",
        "probe": "feshi",
        "jurisdictions": ["TR"],
    }
    picked = {**asked, "result_fields": {"id": "$.document_id"}}
    fetched = client.post("/api/setup/sources/mcp", json=picked, headers=ME)

    assert listed.status_code == 200, listed.text
    assert {"name": "get_document", "description": "One document in full."} in listed.json()
    assert fetched.status_code == 200, fetched.text
    block = fetched.json()["block"]
    assert block["connector"] == "mcp"
    assert block["options"]["search_results"] == "$.hits[*]"
    assert block["options"]["fetch_arguments"] == {"id": "{id}"}
    assert block["jurisdictions"] == ["TR"]


def test_a_provider_profile_connects_with_its_key(fresh: Path):
    os.environ["DOC_KEY"] = DOC_KEY
    api = start_document_api()
    try:
        base = f"http://127.0.0.1:{api.server_port}/v1"
        profile(fresh, "http", http_options(base))
        client = workbench(fresh)
        connected = client.post(
            "/api/setup/sources/profile", json={"given": "provider.yaml"}, headers=ME
        )
    finally:
        api.shutdown()

    assert connected.status_code == 200, connected.text
    found = connected.json()
    assert found["block"]["profile"] == "provider.yaml"
    assert found["block"]["jurisdictions"] == ["TR"]
    assert any("charges per search" in note for note in found["notes"])
    assert DOC_KEY not in connected.text


def test_a_document_api_that_refuses_the_key_says_so(fresh: Path):
    os.environ["DOC_KEY"] = "not-the-key"
    api = start_document_api()
    try:
        client = workbench(fresh)
        connected = client.post(
            "/api/setup/sources/api",
            json={
                "base_url": f"http://127.0.0.1:{api.server_port}/v1",
                "search_path": "/search",
                "fetch_path": "/documents/{id}",
                "key_env": "DOC_KEY",
                "probe": "feshi",
            },
            headers=ME,
        )
    finally:
        api.shutdown()

    assert connected.status_code == 422
    assert "401" in connected.json()["detail"]
    assert "not-the-key" not in connected.text


def test_each_model_is_tested_alone(fresh: Path):
    os.environ["ANTHROPIC_API_KEY"] = "sk-test-0123456789abcdef"
    unreachable = {**JUDGE, "options": {**JUDGE["options"], "base_url": "http://127.0.0.1:9"}}
    client = workbench(fresh)

    tested = client.post("/api/setup/models/test", json={"block": unreachable}, headers=ME)

    assert tested.status_code == 200
    shown = tested.json()
    assert shown["status"] == "not reachable from here"
    assert shown["next"]
    assert "sk-test" not in tested.text


def test_a_second_judge_of_the_same_family_is_refused(fresh: Path):
    project(fresh)
    client = workbench(fresh)
    twin = {**SECOND, "options": {**SECOND["options"], "family": "claude"}}

    same = client.put("/api/settings/sections/judges", json={"value": [JUDGE, twin]}, headers=ME)
    other = client.put("/api/settings/sections/judges", json={"value": [JUDGE, SECOND]}, headers=ME)

    assert same.status_code == 422
    assert "claude family" in same.json()["detail"]
    assert other.status_code == 200
    written = yaml.safe_load((fresh / "casebench.yaml").read_text(encoding="utf-8"))
    assert [j["model"] for j in written["judges"]] == ["claude-judge", "gpt-judge"]


def test_setup_routes_are_an_engineers_on_their_own_machine(fresh: Path):
    reviewer = workbench(fresh, role="reviewer")
    assert reviewer.get("/api/setup/scan", headers=ME).status_code == 403
    assert reviewer.get("/api/session").json()["setting_up"] is False
    assert "corpora" in SECTIONS
