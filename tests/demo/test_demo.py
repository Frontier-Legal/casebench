"""`casebench demo` runs a bundled suite with no key, and asks no model (decision 0061)."""

import socket
from asyncio.proactor_events import BaseProactorEventLoop as ProactorLoop
from asyncio.selector_events import BaseSelectorEventLoop as SelectorLoop
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from casebench.cli import main
from casebench.core.score import CitationLabel
from casebench.demo import PROJECT
from casebench.judge.memo import MEMO_FILE
from casebench.runs.log import RunLog
from casebench.workbench.app import PERSON_HEADER
from tests.perimeter.test_nothing_leaves_the_perimeter import recording


def test_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)  # a new folder, with no corpus cache, as a first run has
    connected: list[tuple[str, int]] = []
    for owner in (socket.socket, SelectorLoop, ProactorLoop):
        name = "connect" if owner is socket.socket else "sock_connect"
        monkeypatch.setattr(owner, name, recording(getattr(owner, name), connected))
    served: dict[str, Any] = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **options: served.update(app=app, **options))
    monkeypatch.setattr("webbrowser.open", lambda url: served.update(opened=url))

    ran = CliRunner().invoke(main, ["demo", "--dir", str(tmp_path / "demo")])
    monkeypatch.undo()
    log = RunLog(tmp_path / "demo" / "runs" / "demo")
    scores = RunLog.read_scores(log.score_sets()[-1])
    labels = {c.label for s in scores for c in s.citations}
    asked = (log.folder / MEMO_FILE).read_text("utf-8").count("\n")
    workbench = TestClient(served["app"], base_url="http://127.0.0.1:7462")
    queue = workbench.get("/api/queue", headers={PERSON_HEADER: quote("Demo")}).json()["items"]
    first = workbench.get(f"/api/items/{queue[0]['key']}", headers={PERSON_HEADER: "Demo"})

    assert ran.exit_code == 0, ran.output
    assert "none is a real decision" in ran.output
    # A bundled suite ran against the echo agent, and every judge reply came from the memo.
    assert len(log.results()) == 6
    assert asked == (PROJECT / MEMO_FILE).read_text("utf-8").count("\n")
    assert RunLog.read_errors(log.score_sets()[-1]) == []
    assert {s.case_id for s in scores if s.metric == "criteria"} == {
        r.case_id for r in log.results()
    }
    assert {CitationLabel.VERIFIED, CitationLabel.MISGROUNDED, CitationLabel.FABRICATED} <= labels
    # The workbench opens with failed answers first, each with the passage it cited.
    assert served["opened"] == "http://127.0.0.1:7462/"
    assert "failed" in queue[0]["flags"]
    assert first.status_code == 200
    assert all(c["quote"] for c in first.json()["citations"])
    # It wrote nothing outside its own folder, and nothing left this machine.
    assert not (tmp_path / ".casebench").exists()
    assert {host for host, _ in connected} <= {"127.0.0.1"}


def test_the_demos_help_names_the_price_lists_it_reads():
    shown = CliRunner().invoke(main, ["demo", "--help"])

    assert shown.exit_code == 0
    assert "no network" not in shown.output
    assert "two public price lists" in shown.output


def test_a_relative_dir_holds_the_demo_itself(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)

    ran = CliRunner().invoke(main, ["demo", "--dir", "demo1", "--no-serve"])

    assert ran.exit_code == 0, ran.output
    assert f"the demo is in {tmp_path.resolve() / 'demo1'}\n" in ran.output
    assert (tmp_path / "demo1" / "runs" / "demo").is_dir()
    assert not (tmp_path / "demo1" / "demo1").exists()
