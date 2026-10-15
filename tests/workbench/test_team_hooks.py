"""What the core gives a team server: an access hook every route checks, an event log the
database keeps append-only, and a lawyer's verdict no judge overwrites (decision 0058)."""

import json
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from click.testing import CliRunner
from fastapi import APIRouter, Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from casebench.cli import main
from casebench.workbench.access import ROLES, Caller
from casebench.workbench.app import create_app
from casebench.workbench.items import answer_key
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Event, Store
from tests.judge.test_judge_rests_on_evidence import judge_block, port, report, run  # noqa: F401
from tests.report.suites import criteria_case
from tests.workbench.test_review_queue import HOST
from tests.workbench.test_review_queue import project as queue_project  # noqa: F401

ANSWER_KEY = answer_key("r1", "answer-1", 0)


class Badge:
    """A stand-in for a team server's access: the caller's role is in a header."""

    mode = "team"

    def caller(self, request: Request) -> Caller | None:
        role = request.headers.get("X-Test-Role")
        if role not in ROLES:
            return None
        return Caller(name=f"the {role}", key=role, role=role, can=ROLES[role])


def team(project: dict[str, Any]) -> TestClient:
    extra = APIRouter()

    @extra.get("/api/team/hello")
    def hello() -> dict[str, str]:
        return {"hello": "team"}

    app = create_app(
        project["workspace"], project["store"], [HOST], access=Badge(), routers=[extra]
    )
    return TestClient(app, base_url=f"http://{HOST}")


def as_role(role: str) -> dict[str, str]:
    return {"X-Test-Role": role}


def test_every_route_checks_the_callers_role(queue_project: dict[str, Any]):  # noqa: F811
    app = team(queue_project)
    verdict = {"verdicts": [{"criterion_id": "c-statute-1", "verdict": "pass"}]}
    change = {"fields": {"question": "Q?", "key points": "+1 Says yes"}, "reason": "x"}

    def status(role: str, method: str, url: str, **body: Any) -> int:
        return app.request(method, url, headers=as_role(role), **body).status_code

    assert app.get("/api/queue").status_code == 401
    assert app.get("/api/session").json()["mode"] == "team"
    me = app.get("/api/me", headers=as_role("viewer")).json()
    assert (me["name"], me["role"], me["role_locked"]) == ("the viewer", "viewer", True)
    assert me["can"] == ["read"]
    assert status("viewer", "GET", "/api/queue") == 200
    assert status("viewer", "POST", f"/api/items/{ANSWER_KEY}/finish", json=verdict) == 403
    assert status("reviewer", "POST", f"/api/items/{ANSWER_KEY}/finish", json=verdict) == 200
    assert status("reviewer", "POST", "/api/golden/drafts", json=change) == 403
    assert status("editor", "POST", "/api/golden/drafts", json=change) == 200
    # The engineering view is the engineer's, whatever an editor's browser asks for.
    app.put("/api/me", json={"name": "x", "view": "engineering"}, headers=as_role("editor"))
    assert app.get("/api/me", headers=as_role("editor")).json()["view"] == "review"
    assert status("editor", "GET", "/api/harness/r1/answer-1/0") == 403
    app.put("/api/me", json={"name": "x", "view": "engineering"}, headers=as_role("engineer"))
    assert status("engineer", "GET", "/api/harness/r1/answer-1/0") == 200
    assert app.get("/api/team/hello").json() == {"hello": "team"}


def test_the_event_log_is_append_only(tmp_path: Path):
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    store.log([Event(by="Ayşe", action="verdict", item="answer:r:c:0", subject="c1")])

    for statement in ("UPDATE events SET by = 'Can'", "DELETE FROM events"):
        with pytest.raises(IntegrityError, match="append-only"), store.engine.begin() as c:
            c.execute(sa.text(statement))

    assert [e.by for e in store.events()] == ["Ayşe"]


def test_a_judge_never_overwrites_a_lawyer(tmp_path: Path, port: int):  # noqa: F811
    """The lawyer fails a criterion the judge passed; the judge runs again and passes it again;
    the lawyer's verdict stands in the report, the gate and the workbench."""
    cases = [criteria_case(1, {"Mentions upheld": 1})]
    assert run(tmp_path, cases, judge=judge_block(port)).exit_code == 0
    folder = tmp_path / "runs" / "r"
    reviewed = CliRunner().invoke(
        main,
        ["review", "criterion", str(folder), "--by", "Ayşe", "--case", "case-001",
         "--criterion", "c1", "--verdict", "fail", "--note", "it names no reason"],
    )  # fmt: skip
    again = run(tmp_path, cases, judge=judge_block(port))
    workspace = Workspace(tmp_path / "runs", [tmp_path / "suite"])
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    app = TestClient(create_app(workspace, store, [HOST]), base_url=f"http://{HOST}")
    app.put("/api/me", json={"name": "Can", "view": "review"})
    item = app.get(
        f"/api/items/{answer_key('r', 'case-001', 0)}", headers={"X-Casebench-Person": "Can"}
    ).json()

    assert reviewed.exit_code == 0, reviewed.output
    assert again.exit_code == 0, again.output
    [score] = [s for s in report(tmp_path)["scores"] if s["case_id"] == "case-001"]
    [verdict] = score["criteria"]
    assert (verdict["met"], verdict["reviewed_by"], verdict["judge_met"]) == (False, "Ayşe", True)
    assert score["value"] == 0.0
    [shown] = item["criteria"]
    assert shown["judge"] == "pass" and shown["lawyer"]["verdict"] == "fail"
    assert (
        json.loads((folder / "reviews.jsonl").read_text(encoding="utf-8").splitlines()[0])["by"]
        == "Ayşe"
    )
