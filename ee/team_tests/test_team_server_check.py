# SPDX-License-Identifier: Elastic-2.0
"""`casebench check` reaches the team server casebench.yaml names, with the engineer's key, and
says what to do when it cannot (decision 0064)."""

import json
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from click.testing import CliRunner

from casebench.cli import main
from casebench_ee.server import Server, build

STARTED_WITHIN = 10.0


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def served(database: str, tmp_path: Path) -> Iterator[tuple[Server, str]]:
    """A team server listening on the loopback address, as `casebench-team serve` runs it."""
    port = free_port()
    public = f"http://127.0.0.1:{port}"
    server = build(database, public, tmp_path / "runs", [tmp_path / "suites"])
    running = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port))
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + STARTED_WITHIN
    while not running.started and time.monotonic() < deadline:
        time.sleep(0.05)
    try:
        yield server, public
    finally:
        running.should_exit = True
        thread.join(STARTED_WITHIN)


def check(tmp_path: Path, url: str, monkeypatch: pytest.MonkeyPatch, key: str | None) -> dict:
    config = tmp_path / "casebench.yaml"
    config.write_text(f"cloud:\n  url: {url}\n", encoding="utf-8")
    if key is None:
        monkeypatch.delenv("CASEBENCH_CLOUD_KEY", raising=False)
    else:
        monkeypatch.setenv("CASEBENCH_CLOUD_KEY", key)
    ran = CliRunner().invoke(main, ["check", "--config", str(config), "--json"])
    report = json.loads(ran.output)
    assert key is None or key not in ran.output
    (part,) = [p for p in report["parts"] if p["part"] == "team server"]
    return part


def test_check_reaches_the_team_server(
    served: tuple[Server, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    server, url = served
    server.team.add("selin@firm.example", "Selin Kaya", "admin", "setup")
    _, engineer = server.team.new_key("Selin's laptop", "engineer", "Selin Kaya")
    _, reviewer = server.team.new_key("A reviewer's key", "reviewer", "Selin Kaya")

    taken = check(tmp_path, url, monkeypatch, engineer)
    unset = check(tmp_path, url, monkeypatch, None)
    wrong = check(tmp_path, url, monkeypatch, "cbk_not-a-key-this-server-made")
    lower = check(tmp_path, url, monkeypatch, reviewer)
    nowhere = check(tmp_path, f"http://127.0.0.1:{free_port()}", monkeypatch, engineer)

    assert taken["passed"], taken
    assert "took the key as an engineer's" in taken["reason"]
    assert not unset["passed"] and "no API key in CASEBENCH_CLOUD_KEY" in unset["reason"]
    assert "engineer role, made on its Team page" in unset["next"]
    assert not wrong["passed"] and "refused the key" in wrong["reason"]
    assert "set it as CASEBENCH_CLOUD_KEY" in wrong["next"]
    assert not lower["passed"] and "its role cannot push runs" in lower["reason"]
    assert nowhere["status"] == "not reachable from here"
