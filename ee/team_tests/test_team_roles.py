# SPDX-License-Identifier: Elastic-2.0
"""Five roles, each including the one before, on real sign-ins and API keys (decision 0058)."""

from pathlib import Path
from typing import Any

from casebench.workbench.items import answer_key
from team_tests.helpers import browser, serve, signed_in

ANSWER = answer_key("r1", "answer-1", 0)
VERDICT = {"verdicts": [{"criterion_id": "c-statute-1", "verdict": "pass"}]}
NEW_CASE = {"fields": {"question": "Q?", "key points": "+1 Says yes"}, "reason": "a client asked"}


def test_roles(database: str, tmp_path: Path):
    server = serve(database, tmp_path)
    people = {
        role: signed_in(server, f"{role}@firm.example", f"The {role}", role)
        for role in ("viewer", "reviewer", "editor", "engineer", "admin")
    }

    def status(role: str, method: str, url: str, **body: Any) -> int:
        return people[role].request(method, url, **body).status_code

    for app in people.values():
        app.put("/api/me", json={"name": "ignored", "view": "engineering"})
    rows = {
        "read the queue": [status(r, "GET", "/api/queue") for r in people],
        "read a report": [status(r, "GET", "/api/runs/r1/report") for r in people],
        "give verdicts": [status(r, "POST", f"/api/items/{ANSWER}/reserve") for r in people],
        "compare blind": [
            status(r, "POST", "/api/compare/r1/r2/answer-1/0", json={"choice": "a", "reason": "x"})
            for r in people
        ],
        "change golden data": [
            status(r, "POST", "/api/golden/missing-suite", json=NEW_CASE) for r in people
        ],
        "the harness view": [status(r, "GET", "/api/harness/r1/answer-1/0") for r in people],
        "manage people": [status(r, "GET", "/api/team/users") for r in people],
        "set limits": [
            status(r, "PUT", "/api/team/limits", json={"team": 5, "person": 1}) for r in people
        ],
    }

    # viewer, reviewer, editor, engineer, admin; 404 is allowed but not found, 409 held.
    assert rows["read the queue"] == [200] * 5
    assert rows["read a report"] == [200] * 5
    assert rows["give verdicts"][0] == 403 and all(
        s in (200, 409) for s in rows["give verdicts"][1:]
    )
    assert rows["compare blind"][0] == 403 and set(rows["compare blind"][1:]) == {404}
    assert rows["change golden data"][:2] == [403, 403] and set(rows["change golden data"][2:]) == {
        404
    }
    assert rows["the harness view"] == [403, 403, 403, 200, 200]
    assert rows["manage people"] == [403, 403, 403, 403, 200]
    assert rows["set limits"] == [403, 403, 403, 403, 200]
    # Only an engineer or an admin keeps the engineering view they asked for.
    views = [app.get("/api/me").json()["view"] for app in people.values()]
    assert views == ["review", "review", "review", "engineering", "engineering"]


def test_api_keys_for_ci_and_limits(database: str, tmp_path: Path):
    server = serve(database, tmp_path)
    admin = signed_in(server, "admin@firm.example", "The admin", "admin")

    made = admin.post("/api/team/keys", json={"name": "CI", "role": "engineer"}).json()
    ci = browser(server)
    ci.headers["Authorization"] = f"Bearer {made['token']}"
    allowed = ci.get("/api/runs")
    no_admin = admin.post("/api/team/keys", json={"name": "root", "role": "admin"})
    admin.post(f"/api/team/keys/{made['key']['id']}/revoke")
    revoked = ci.get("/api/runs")
    admin.put("/api/team/limits", json={"team": 5, "person": 1.5})
    reviewer = signed_in(server, "ayse@firm.example", "Ayşe", "reviewer")
    budget = reviewer.get("/api/try").json()
    me = server.team.by_email("admin@firm.example")
    assert me is not None
    last_admin = admin.patch(f"/api/team/users/{me.id}", json={"role": "editor"})

    assert made["token"].startswith("cbk_") and made["key"]["role"] == "engineer"
    assert allowed.status_code == 200
    assert no_admin.status_code == 422
    assert revoked.status_code == 401
    assert budget["limit"] == 5
    assert last_admin.status_code == 422 and "one admin" in last_admin.json()["detail"]
    stored = [k.token for k in server.team.api_keys()]
    assert made["token"] not in stored
