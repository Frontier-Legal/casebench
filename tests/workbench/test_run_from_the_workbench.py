"""An engineer sees what a run will send, starts it, follows it and opens its results, all in
the workbench; the run is the `casebench run` a terminal starts (decision 0063)."""

import time
from pathlib import Path
from urllib.parse import quote

import yaml
from fastapi.testclient import TestClient

from casebench.config import load_config
from casebench.runs.log import RunLog
from casebench.setup.init_cli import HEADER
from casebench.workbench.app import PERSON_HEADER, create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from tests.report.suites import frozen, mixed

HOST = "testserver"
ME = {PERSON_HEADER: quote("Deniz")}
AGENTS = Path(__file__).parents[1] / "report" / "agents.py"
# Long enough for a child process to start, answer and score three cases on a slow runner.
FINISHES_WITHIN_S = 120


def workbench(folder: Path) -> TestClient:
    path = folder / "casebench.yaml"
    config = load_config(path)
    workspace = Workspace(folder / "runs", [folder / "suites"], None, config.agent_models)
    store = Store(f"sqlite:///{folder / 'casebench.db'}")
    app = create_app(workspace, store, [HOST], config=config, config_path=path, folder=folder)
    client = TestClient(app, base_url=f"http://{HOST}")
    client.put("/api/me", json={"name": "Deniz", "view": "engineering"}, headers=ME)
    return client


def test_run_from_the_workbench(tmp_path: Path):
    settings = {"target": {"type": "python", "entry": f"{AGENTS}:from_facts"}}
    (tmp_path / "casebench.yaml").write_text(HEADER + yaml.safe_dump(settings), encoding="utf-8")
    frozen(mixed(3), tmp_path / "suites" / "outcomes")
    client = workbench(tmp_path)

    suites = client.get("/api/run/suites", headers=ME).json()
    assert [(s["suite_id"], s["cases"], s["first"]) for s in suites] == [("outcomes", 3, False)]

    plan = client.post("/api/run/plan", json={"suite_id": "outcomes"}, headers=ME).json()
    assert plan["can_start"] is True
    assert plan["lines"][0].startswith("target: 3 calls")
    assert plan["lines"][-1] == "nothing was sent"
    assert not (tmp_path / "runs").exists()

    started = client.post("/api/run/start", json={"suite_id": "outcomes"}, headers=ME)
    assert started.status_code == 200
    assert started.json()["state"] == "running"
    again = client.post("/api/run/start", json={"suite_id": "outcomes"}, headers=ME)
    assert again.status_code in (200, 409)

    deadline = time.monotonic() + FINISHES_WITHIN_S
    seen: list[str] = []
    while True:
        job = client.get(f"/api/run/current?since={len(seen)}", headers=ME).json()
        seen += job["lines"]
        if job["state"] != "running" or time.monotonic() > deadline:
            break
        time.sleep(0.2)
    assert job["state"] == "finished", "\n".join(seen)
    assert (job["answered"], job["scored"], job["total"]) == (3, 3, 3)
    assert job["line_count"] == len(seen)
    assert any(line.startswith("open it in the workbench") for line in seen)

    run_id = job["run_id"]
    log = RunLog(tmp_path / "runs" / run_id)
    assert len(log.results()) == 3 and log.score_sets()
    runs = client.get("/api/runs", headers=ME).json()
    assert runs[0]["run_id"] == run_id and runs[0]["scored"] is True

    # Resuming the run sends nothing it has an answer for.
    resumed = {"suite_id": "outcomes", "run_id": run_id}
    again_plan = client.post("/api/run/plan", json=resumed, headers=ME).json()
    assert again_plan["lines"][0].startswith("target: 0 calls (3 cases already stored)")
    unknown = client.post("/api/run/start", json={**resumed, "run_id": "no-such-run"}, headers=ME)
    assert unknown.status_code == 404


def test_a_run_that_cannot_start_says_why(tmp_path: Path):
    (tmp_path / "casebench.yaml").write_text(HEADER + "network:\n  allow: []\n", encoding="utf-8")
    (tmp_path / "suites").mkdir()
    client = workbench(tmp_path)
    assert client.get("/api/run/suites", headers=ME).json() == []
    plan = client.post("/api/run/plan", json={}, headers=ME).json()
    assert plan["can_start"] is False
    assert "no target" in plan["why_not"]
    refused = client.post("/api/run/start", json={}, headers=ME)
    assert refused.status_code == 422
    assert client.get("/api/run/current", headers=ME).json() is None
