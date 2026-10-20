"""init opens the workbench for a person at a terminal, and never for a script (decision 0065)."""

import os
import socket
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from casebench import keys
from casebench.cli import main
from casebench.setup import init_cli
from casebench.workbench.app import PERSON_HEADER
from casebench.workbench.cli import free_port

CATALOG = Path(__file__).parent / "catalog.json"
AGENT = """\
from openai import OpenAI

client = OpenAI()


def answer(question):
    return client.chat.completions.create(model="real-model", messages=[]).choices[0]
"""
FLAGS = [
    "--entry",
    "agent.py:answer",
    "--corpus",
    "none",
    "--no-judge",
    "--no-extract",
    "--no-live",
    "--no-routes",
    "--yes",
    "--catalog",
    str(CATALOG),
]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(keys, "_held", {})
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    return tmp_path


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """The workbench init would serve, and the page the browser would open, held here."""
    held: dict[str, Any] = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **options: held.update(app=app, **options))
    monkeypatch.setattr("webbrowser.open", lambda url: held.update(opened=url))
    return held


def test_init_opens_the_workbench(project: Path, served: dict[str, Any]):
    made = CliRunner().invoke(main, ["init", *FLAGS, "--ui"])

    assert made.exit_code == 0, made.output
    assert (project / "casebench.yaml").is_file()
    assert "The workbench opens on Home" in made.output
    assert served["opened"].startswith("http://127.0.0.1:")
    workbench = TestClient(served["app"], base_url=f"http://127.0.0.1:{served['port']}")
    assert workbench.get("/api/session").json()["setting_up"] is False


def test_setting_up_in_the_browser(
    project: Path, served: dict[str, Any], monkeypatch: pytest.MonkeyPatch
):
    asked: list[list[str]] = []

    def pick(question: str, choices: list[tuple[str, str]], default: str | None = None) -> str:
        asked.append([value for _, value in choices])
        return init_cli.BROWSER

    monkeypatch.setattr(init_cli, "interactive", lambda: True)
    monkeypatch.setattr(init_cli, "pick", pick)

    made = CliRunner().invoke(main, ["init"])

    assert made.exit_code == 0, made.output
    assert asked == [[init_cli.BROWSER, "quick", "custom"]]
    # Nothing is written until the guide saves it, and the guide comes first.
    assert not (project / "casebench.yaml").exists()
    workbench = TestClient(served["app"], base_url=f"http://127.0.0.1:{served['port']}")
    assert workbench.get("/api/session").json()["setting_up"] is True
    me = {PERSON_HEADER: quote("Deniz")}
    workbench.put("/api/me", json={"name": "Deniz", "view": "engineering"}, headers=me)
    found = workbench.get("/api/setup/scan", headers=me).json()
    assert found["entries"] == ["agent.py:answer"]
    assert found["models"] == ["real-model"]


def test_no_terminal_no_server(project: Path, served: dict[str, Any]):
    made = CliRunner().invoke(main, ["init", *FLAGS])

    assert made.exit_code == 0, made.output
    assert (project / "casebench.yaml").is_file()
    # A coding agent or CI runs init with no terminal; a server would never return to it.
    assert served == {}


def test_a_taken_port_is_not_fought_over():
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        busy = taken.getsockname()[1]
        assert free_port(busy) != busy
    # Once nothing listens on it, the preferred port is the one used.
    assert free_port(busy) == busy
