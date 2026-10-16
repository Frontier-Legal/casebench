"""The Settings page shows what each part of the setup is for and costs, and saves every change
to casebench.yaml (decision 0063)."""

import json
import os
import stat
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest
import yaml
from fastapi.testclient import TestClient

from casebench.config import load_config
from casebench.setup import catalog as model_catalog
from casebench.setup.init_cli import HEADER
from casebench.workbench.app import PERSON_HEADER, create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store

HOST = "testserver"
ME = {PERSON_HEADER: quote("Deniz")}
CATALOG = Path(__file__).parents[1] / "setup" / "catalog.json"
KEY = "sk-test-0123456789abcdef"
JUDGE = {
    "provider": "anthropic",
    "model": "claude-judge",
    "options": {"api_key_env": "ANTHROPIC_API_KEY", "max_tokens": 4096, "family": "claude"},
    "context_window": 200000,
    "price": {"input": 3.0, "output": 15.0},
}
SECOND = {
    "provider": "openai",
    "model": "gpt-judge",
    "options": {"api_key_env": "OPENAI_API_KEY", "family": "gpt"},
    "price": {"input": 1.25, "output": 10.0},
}
SETTINGS = {
    "target": {"type": "python", "entry": "agent.py:answer"},
    "agent_models": [
        {"model": "qwen-agent", "family": "qwen", "price": {"input": 0.2, "output": 0.6}}
    ],
    "judge": JUDGE,
    "workbench": {"try_daily_limit_usd": 5.0},
    "keys": {"ANTHROPIC_API_KEY": ".env"},
}


def project(folder: Path, settings: dict | None = None, comment: str = "") -> Path:
    (folder / "agent.py").write_text("def answer(question):\n    return 'No.'\n", "utf-8")
    path = folder / "casebench.yaml"
    path.write_text(HEADER + comment + yaml.safe_dump(settings or SETTINGS, sort_keys=False))
    return path


def workbench(folder: Path, role: str | None = None) -> TestClient:
    path = folder / "casebench.yaml"
    config = load_config(path) if path.is_file() else None
    workspace = Workspace(folder / "runs", [folder], None, config.agent_models if config else [])
    store = Store(f"sqlite:///{folder / 'casebench.db'}")
    app = create_app(workspace, store, [HOST], role, config=config, config_path=path, folder=folder)
    client = TestClient(app, base_url=f"http://{HOST}")
    client.put("/api/me", json={"name": "Deniz", "view": "engineering"}, headers=ME)
    return client


@pytest.fixture
def keyed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project whose judge's key is in its .env file, which git ignores."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env").write_text(f"ANTHROPIC_API_KEY={KEY}\n", encoding="utf-8")
    project(tmp_path)
    return tmp_path


def test_settings_show_what_is_used_for_what(keyed: Path):
    client = workbench(keyed)
    me = client.get("/api/me", headers=ME).json()
    assert me["setup"] is True

    response = client.get("/api/settings", headers=ME)
    assert response.status_code == 200
    shown = response.json()
    (judge,) = shown["models"]
    assert judge["role"] == "judge"
    assert "citations" in judge["used_for"]
    assert (judge["provider"], judge["model"], judge["family"]) == (
        "anthropic",
        "claude-judge",
        "claude",
    )
    assert (judge["price_input"], judge["price_output"]) == (3.0, 15.0)
    assert (judge["max_tokens"], judge["context_window"]) == (4096, 200000)
    assert judge["key"] == "ANTHROPIC_API_KEY"
    keys = {k["name"]: k for k in shown["keys"]}
    assert keys["ANTHROPIC_API_KEY"]["where"] == "file"
    assert keys["ANTHROPIC_API_KEY"]["used_by"] == ["judge"]
    assert shown["budget"]["limit"] == 5.0
    assert shown["budget"]["spent_today"] == 0
    assert shown["sections"]["judges"] == [JUDGE]
    assert "anthropic" in shown["plugins"]["providers"]
    assert "python" in shown["plugins"]["targets"]
    # A key is never part of what the page is sent.
    assert KEY not in response.text


def test_a_saved_setting_takes_effect(keyed: Path):
    client = workbench(keyed)
    saved = client.put(
        "/api/settings/sections/workbench",
        json={"value": {"try_daily_limit_usd": 2.5, "second_approval": True}},
        headers=ME,
    )
    assert saved.status_code == 200
    assert client.get("/api/try", headers=ME).json()["limit"] == 2.5
    assert client.get("/api/golden", headers=ME).json()["second_approval"] is True

    two = client.put("/api/settings/sections/judges", json={"value": [JUDGE, SECOND]}, headers=ME)
    assert [m["role"] for m in two.json()["models"]] == ["judge", "second judge"]
    text = (keyed / "casebench.yaml").read_text(encoding="utf-8")
    assert text.startswith(HEADER)
    written = yaml.safe_load(text)
    assert written["judges"] == [JUDGE, SECOND] and "judge" not in written
    assert written["workbench"] == {"try_daily_limit_usd": 2.5, "second_approval": True}
    assert written["target"] == SETTINGS["target"]
    assert load_config(keyed / "casebench.yaml").workbench.try_daily_limit_usd == 2.5  # type: ignore[union-attr]

    removed = client.put("/api/settings/sections/workbench", json={"value": None}, headers=ME)
    assert removed.status_code == 200
    assert "workbench" not in yaml.safe_load((keyed / "casebench.yaml").read_text())


def test_a_setting_that_does_not_validate_changes_nothing(keyed: Path):
    client = workbench(keyed)
    path = keyed / "casebench.yaml"
    before = path.read_bytes()
    refused = client.put(
        "/api/settings/sections/judges", json={"value": [{"provider": "anthropic"}]}, headers=ME
    )
    assert refused.status_code == 422
    assert "judges.0.model" in refused.json()["detail"]
    broken = client.put("/api/settings/file", json={"text": "judge: [unclosed"}, headers=ME)
    assert broken.status_code == 422
    assert "not YAML" in broken.json()["detail"]
    assert path.read_bytes() == before
    assert client.get("/api/try", headers=ME).json()["limit"] == 5.0


def test_the_whole_file_is_editable(keyed: Path):
    client = workbench(keyed)
    text = (
        HEADER
        + "# The judge we pay for.\n"
        + yaml.safe_dump({**SETTINGS, "network": {"allow": ["api.example.com"]}}, sort_keys=False)
    )
    saved = client.put("/api/settings/file", json={"text": text}, headers=ME)
    assert saved.status_code == 200
    assert (keyed / "casebench.yaml").read_text(encoding="utf-8") == text
    assert saved.json()["sections"]["network"] == {"allow": ["api.example.com"]}
    # A section saved later rewrites the file, so the page warns that the comment would go.
    assert saved.json()["has_comments"] is True


def test_a_key_set_in_the_workbench_stays_out_of_git(keyed: Path):
    client = workbench(keyed)
    secret = "sk-openai-fedcba9876543210"
    client.put("/api/settings/sections/judges", json={"value": [JUDGE, SECOND]}, headers=ME)
    before = {k["name"]: k["where"] for k in client.get("/api/settings", headers=ME).json()["keys"]}
    assert before["OPENAI_API_KEY"] == "missing"

    response = client.put("/api/settings/keys/OPENAI_API_KEY", json={"value": secret}, headers=ME)
    assert response.status_code == 200
    assert secret not in response.text
    keys = {k["name"]: k for k in response.json()["keys"]}
    assert keys["OPENAI_API_KEY"]["where"] == "file"
    assert keys["OPENAI_API_KEY"]["file"] == ".casebench/.env"

    kept = keyed / ".casebench" / ".env"
    assert kept.read_text(encoding="utf-8") == f"OPENAI_API_KEY={secret}\n"
    if os.name == "posix":
        assert stat.S_IMODE(kept.stat().st_mode) == 0o600
    written = yaml.safe_load((keyed / "casebench.yaml").read_text())
    assert written["keys"] == {"ANTHROPIC_API_KEY": ".env", "OPENAI_API_KEY": ".casebench/.env"}
    untracked = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=keyed,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert ".env" not in untracked.replace(".gitignore", "")

    # The judge's key, in a file git ignores already, is changed where it is.
    client.put(
        "/api/settings/keys/ANTHROPIC_API_KEY", json={"value": "sk-new-key-123456"}, headers=ME
    )
    assert (keyed / ".env").read_text(encoding="utf-8") == "ANTHROPIC_API_KEY=sk-new-key-123456\n"


def test_a_judge_is_picked_from_the_model_catalog(keyed: Path, monkeypatch: pytest.MonkeyPatch):
    saved = json.loads(CATALOG.read_text(encoding="utf-8"))
    fetched: list[str] = []

    def load(path: Path | None = None) -> dict:
        fetched.append("catalog")
        return saved

    monkeypatch.setattr(model_catalog, "load", load)
    client = workbench(keyed)
    providers = client.get("/api/settings/catalog", headers=ME).json()
    assert {"id": "anthropic", "name": "Anthropic", "models": 1} in providers
    (model,) = client.get("/api/settings/catalog/anthropic", headers=ME).json()
    assert (model["id"], model["family"], model["max_output"]) == ("judge-model", "claude", 256)

    picked = client.post(
        "/api/settings/catalog/model",
        json={"provider": "anthropic", "model": "judge-model"},
        headers=ME,
    ).json()
    block = picked["block"]
    assert (block["provider"], block["model"]) == ("anthropic", "judge-model")
    assert block["options"]["api_key_env"] == "ANTHROPIC_API_KEY"
    assert picked["missing"] == []
    # The catalog is fetched once, when the picker first opens.
    assert fetched == ["catalog"]

    saved_judge = client.put("/api/settings/sections/judges", json={"value": [block]}, headers=ME)
    assert saved_judge.status_code == 200
    assert saved_judge.json()["models"][0]["model"] == "judge-model"


def test_the_setup_is_checked_from_the_page(keyed: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    unreachable = {**JUDGE, "options": {**JUDGE["options"], "base_url": "http://127.0.0.1:9"}}
    project(keyed, {**SETTINGS, "judge": unreachable})
    client = workbench(keyed)
    checked = client.post("/api/settings/check", headers=ME)
    assert checked.status_code == 200
    parts = {part["part"]: part for part in checked.json()}
    assert parts["target"]["passed"] is True
    assert parts["target"]["reason"].startswith('answered "No."')
    assert parts["judge"]["status"] == "not reachable from here"
    assert parts["judge"]["next"]
    assert KEY not in checked.text


def test_settings_and_runs_are_an_engineers_on_their_own_machine(keyed: Path):
    reviewer = workbench(keyed, role="reviewer")
    assert reviewer.get("/api/me", headers=ME).json()["setup"] is False
    assert reviewer.get("/api/settings", headers=ME).status_code == 403
    assert reviewer.post("/api/run/plan", json={}, headers=ME).status_code == 403

    # A workbench told no casebench.yaml, as a team server builds it, serves neither page.
    store = Store(f"sqlite:///{keyed / 'team.db'}")
    served = create_app(Workspace(keyed / "runs", [keyed]), store, [HOST])
    team = TestClient(served, base_url=f"http://{HOST}")
    team.put("/api/me", json={"name": "Deniz", "view": "engineering"}, headers=ME)
    assert team.get("/api/me", headers=ME).json()["setup"] is False
    assert team.get("/api/settings", headers=ME).status_code == 404
    assert team.get("/api/run/suites", headers=ME).status_code == 404
