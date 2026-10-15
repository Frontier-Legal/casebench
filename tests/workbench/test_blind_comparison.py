"""Two runs of one suite compared blind by lawyers (decision 0054). The keyboard is tested with
the web app, in workbench/src/compare.test.tsx."""

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from casebench.cli import main
from casebench.report.preferences import Preference, a_is_first, by_area, read_preferences
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.producer import Producer
from casebench.suites.freeze import freeze
from casebench.workbench.app import create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from tests.workbench.test_partner_report import AREAS, case, scores_for
from tests.workbench.test_review_queue import HOST, as_


def run(runs: Path, run_id: str, suite_hash: str, said: str) -> RunLog:
    log = RunLog.create(
        runs / run_id,
        RunInfo(run_id=run_id, suite_id="suite", suite_hash=suite_hash, target="agent"),
    )
    for case_id in AREAS:
        log.append(Result(case_id=case_id, output=f"{said} answer to {case_id}."))
    log.write_score_set([s for c in AREAS for s in scores_for(c)], Producer(metrics={}))
    return log


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Any]:
    suite = freeze("suite", [case(c) for c in AREAS], tmp_path / "suites" / "suite")
    run(tmp_path / "runs", "r1", suite.content_hash, "The earlier")
    later = run(tmp_path / "runs", "r2", suite.content_hash, "The later")
    other = RunInfo(run_id="r3", suite_id="other", suite_hash="sha256:other", target="agent")
    RunLog.create(tmp_path / "runs" / "r3", other)
    workspace = Workspace(tmp_path / "runs", [tmp_path / "suites"])
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    return {"tmp": tmp_path, "workspace": workspace, "store": store, "later": later}


def client(project: dict[str, Any]) -> TestClient:
    app = create_app(project["workspace"], project["store"], [HOST])
    return TestClient(app, base_url=f"http://{HOST}")


def letter(case_id: str, run: str) -> str:
    """The letter the answer of `run` is shown under."""
    return "a" if a_is_first("r1", "r2", case_id, 0) == (run == "r1") else "b"


def test_blind_a_b(project: dict[str, Any]):
    app = client(project)
    url = "/api/compare/r1/r2"
    before = app.get(url, headers=as_("Ayşe")).json()
    shown = app.get(f"{url}/c1/0", headers=as_("Ayşe")).json()
    unexplained = app.post(f"{url}/c1/0", json={"choice": "a"}, headers=as_("Ayşe"))
    # The later run is preferred on both labour cases; on tax, a tie and a loss.
    given = {
        "c1": letter("c1", "r2"),
        "c2": letter("c2", "r2"),
        "c3": "equal",
        "c4": letter("c4", "r2"),
    }
    for case_id, choice in given.items():
        app.post(
            f"{url}/{case_id}/0",
            json={"choice": choice, "reason": f"reason for {case_id}"},
            headers=as_("Ayşe"),
        )
    # A second look at c4: the earlier answer was better. The latest preference counts.
    revealed = app.post(
        f"{url}/c4/0",
        json={"choice": letter("c4", "r1"), "reason": "it cites the right article"},
        headers=as_("Can"),
    ).json()
    after = app.get(url, headers=as_("Ayşe")).json()
    mixed = app.get("/api/compare/r1/r3", headers=as_("Ayşe"))
    printed = CliRunner().invoke(
        main, ["compare", str(project["tmp"] / "runs/r1"), str(project["tmp"] / "runs/r2")]
    )

    assert [(p["case_id"], p["given"]) for p in before["pairs"]] == [
        ("c1", False), ("c2", False), ("c3", False), ("c4", False),
    ]  # fmt: skip
    assert before["areas"] == []
    # Answers are labelled A and B in an order that differs from case to case, and nothing
    # names a run until a preference is given.
    assert {a_is_first("r1", "r2", c, 0) for c in AREAS} == {True, False}
    assert {shown["a"], shown["b"]} == {"The earlier answer to c1.", "The later answer to c1."}
    assert shown["given"] is None and "r1" not in json.dumps(shown)
    assert shown["inputs"][0]["text"] == "Was dismissal c1 valid?"
    assert [f["kind"] for f in shown["reference"]] == ["outcome", "statute"]
    assert unexplained.status_code == 422 and "needs a reason" in unexplained.json()["detail"]
    assert revealed["given"]["by"] == "Can"
    runs = {revealed["given"]["a_run"], revealed["given"]["b_run"]}
    assert runs == {"r1", "r2"}
    # Wins, losses and ties per practice area; too few pairs to be significant.
    areas = {
        a["practice_area"]: (a["n"], a["wins"], a["losses"], a["ties"], a["significant"])
        for a in after["areas"]
    }
    assert areas == {"labour": (2, 2, 0, 0, False), "tax": (2, 0, 1, 1, False)}
    assert all(p["given"] for p in after["pairs"])
    # Kept in the later run's folder, every preference, and in the event log.
    kept = read_preferences(project["later"].folder)
    assert len(kept) == 5 and kept[-1].choice == "first" and kept[-1].against == "r1"
    logged = [e for e in project["store"].events() if e.action == "preferred"]
    assert len(logged) == 5 and logged[-1].reason == "it cites the right article"
    assert mixed.status_code == 422
    assert printed.exit_code == 0, printed.output
    assert "labour: 2 wins, 0 losses, 0 ties over 2 pairs" in printed.output
    assert "not significant" in printed.output


def test_many_wins_one_way_are_significant():
    """The sign test and the interval agree once enough pairs go one way."""
    given = {
        (f"c{n}", 0): Preference(
            against="r1", case_id=f"c{n}", repeat=0, shown_as_a="first", choice="second",
            reason="better", by="Ayşe",
        )
        for n in range(8)
    }  # fmt: skip
    few = dict(list(given.items())[:3])

    [many] = by_area(given, {}, "suite")
    [three] = by_area(few, {}, "suite")

    assert (many.wins, many.significant) == (8, True)
    assert (three.wins, three.low, three.significant) == (3, 1.0, False)
