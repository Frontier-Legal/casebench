"""Golden data changes only when a second editor approves (decision 0052)."""

from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from casebench.cases.build import Written, lawyer_case
from casebench.core.case import Approval
from casebench.suites.freeze import freeze, load
from casebench.workbench.app import PERSON_HEADER, create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store

HOST = "testserver"


def as_(name: str) -> dict[str, str]:
    return {PERSON_HEADER: quote(name)}


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Any]:
    written = Written(
        question="Is notice required before dismissing for a valid reason?",
        answer="Yes: the notice periods of İş Kanunu m. 17 apply.",
        statutes=["4857 sayılı İş Kanunu m. 17"],
    )
    case = lawyer_case("labour-1", written, "Ayşe", None)
    folder = tmp_path / "suites" / "labour"
    freeze("labour", [case], folder)
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    workspace = Workspace(tmp_path / "runs", [tmp_path / "suites"])
    return {"folder": folder, "store": store, "workspace": workspace}


def client(project: dict[str, Any], role: str | None = None) -> TestClient:
    app = create_app(project["workspace"], project["store"], [HOST], role)
    return TestClient(app, base_url=f"http://{HOST}")


def test_four_eye_approval(project: dict[str, Any]):
    app = client(project)
    before_hash = load(project["folder"])[0].content_hash
    detail = app.get("/api/golden/labour/labour-1", headers=as_("Ayşe")).json()
    fields = {f["name"]: f["value"] for f in detail["fields"]}
    amended = "Yes, but the 2025 amendment shortens the notice periods of İş Kanunu m. 17."
    unexplained = app.put(
        "/api/golden/labour/labour-1",
        json={"fields": {**fields, "reference answer": amended}, "reason": ""},
        headers=as_("Ayşe"),
    )
    proposed = app.put(
        "/api/golden/labour/labour-1",
        json={
            "fields": {**fields, "reference answer": amended},
            "reason": "statute amended in 2025",
        },
        headers=as_("Ayşe"),
    )
    unchanged = load(project["folder"])
    mine = app.get("/api/queue", headers=as_("Ayşe")).json()["items"]
    theirs = app.get("/api/queue", headers=as_("Can")).json()["items"]
    key = f"change:{proposed.json()['proposal']}"
    opened = app.get(f"/api/items/{key}", headers=as_("Can")).json()
    own = app.post(f"/api/items/{key}/finish", json={"decision": "approve"}, headers=as_("Ayşe"))
    approved = app.post(
        f"/api/items/{key}/finish", json={"decision": "approve"}, headers=as_("Can")
    )

    assert fields["reference answer"] == "Yes: the notice periods of İş Kanunu m. 17 apply."
    assert unexplained.status_code == 422 and "say why" in unexplained.json()["detail"]
    assert proposed.status_code == 200, proposed.text
    # Until the second editor approves, the suite is as it was.
    assert unchanged[0].content_hash == before_hash
    assert key not in [i["key"] for i in mine]
    assert key in [i["key"] for i in theirs]
    # The second editor sees the diff, the author, the time and the reason.
    [change] = opened["changes"]
    assert change == {
        "field": "reference answer",
        "before": "Yes: the notice periods of İş Kanunu m. 17 apply.",
        "after": amended,
    }
    assert opened["proposal"]["author"] == "Ayşe"
    assert opened["proposal"]["reason"] == "statute amended in 2025"
    assert opened["proposal"]["at"]
    assert own.status_code == 422 and "not its author" in own.json()["detail"]
    assert approved.status_code == 200, approved.text
    manifest, [case] = load(project["folder"])
    assert manifest.content_hash != before_hash
    [answer] = [f for f in case.reference.facts if f.kind == "answer"]
    assert answer.value == amended and case.approval is Approval.APPROVED
    # The statute the lawyer left as it was keeps its evidence.
    [statute] = [f for f in case.reference.facts if f.kind == "statute"]
    assert statute.evidence.note == "written by Ayşe"
    # The log keeps both the change and the approval.
    logged = [(e.action, e.by, e.reason) for e in project["store"].events(key)]
    assert logged[:2] == [
        ("proposed", "Ayşe", "statute amended in 2025"),
        ("approved", "Can", None),
    ]


def test_new_case_from_the_form(project: dict[str, Any]):
    app = client(project)
    reviewer = client(project, role="reviewer")
    blank = app.get("/api/golden/forms/qa", headers=as_("Ayşe")).json()
    fields = {
        "question": "Can an employer dismiss for refusing overtime?",
        "facts": "The contract does not mention overtime.",
        "reference answer": "No: overtime needs the worker's consent each year.",
        "key points": "+5 Says overtime needs consent\n-3 Says refusal is a valid reason",
        "statutes": "4857 sayılı İş Kanunu m. 41",
    }

    refused = reviewer.post("/api/golden/labour", json={"fields": fields}, headers=as_("Rıza"))
    created = app.post(
        "/api/golden/labour", json={"task": "qa", "fields": fields}, headers=as_("Ayşe")
    )
    _, cases = load(project["folder"])
    row = next(
        c for s in app.get("/api/golden", headers=as_("Can")).json()["suites"] for c in s["cases"]
        if c["case_id"] == created.json()["case_id"]
    )  # fmt: skip
    key = f"change:{created.json()['proposal']}"
    approved = app.post(
        f"/api/items/{key}/finish", json={"decision": "approve"}, headers=as_("Can")
    )
    _, after = load(project["folder"])

    assert [f["name"] for f in blank] == [
        "question", "facts", "reference answer", "key points", "statutes", "precedents",
    ]  # fmt: skip
    assert refused.status_code == 403
    assert created.status_code == 200, created.text
    new = next(c for c in cases if c.id == created.json()["case_id"])
    # Saved as a draft awaiting a second editor.
    assert new.approval is Approval.DRAFT and new.reference.author == "Ayşe"
    assert [(c.text, c.weight) for c in new.reference.criteria] == [
        ("Says overtime needs consent", 5),
        ("Says refusal is a valid reason", -3),
    ]
    assert row["approval"] == "draft" and row["waiting"]["kind"] == "new"
    assert approved.status_code == 200, approved.text
    assert next(c for c in after if c.id == new.id).approval is Approval.APPROVED


def test_a_rejected_new_case_leaves_its_suite(project: dict[str, Any]):
    app = client(project)
    created = app.post(
        "/api/golden/labour",
        json={"fields": {"question": "Q?", "key points": "+1 Says yes"}},
        headers=as_("Ayşe"),
    ).json()
    key = f"change:{created['proposal']}"

    silent = app.post(f"/api/items/{key}/finish", json={"decision": "reject"}, headers=as_("Can"))
    rejected = app.post(
        f"/api/items/{key}/finish",
        json={"decision": "reject", "note": "a duplicate of labour-1"},
        headers=as_("Can"),
    )

    assert silent.status_code == 422
    assert rejected.status_code == 200, rejected.text
    assert [c.id for c in load(project["folder"])[1]] == ["labour-1"]
