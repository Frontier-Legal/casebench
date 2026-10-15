# SPDX-License-Identifier: Elastic-2.0
"""The audit log shows who changed what, when, before, after and why, and nothing can remove an
entry, not even the database's own user (decision 0058)."""

from pathlib import Path

import psycopg
import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError

from casebench.cases.golden import cells_of
from casebench.workbench.items import answer_key
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Event
from team_tests.helpers import serve, signed_in


def test_append_only_audit(postgres: str, tmp_path: Path):
    server = serve(postgres, tmp_path)
    editor = signed_in(server, "selin@firm.example", "Selin Kaya", "editor")
    reviewer = signed_in(server, "ayse@firm.example", "Ayşe Yılmaz", "reviewer")
    admin = signed_in(server, "can@firm.example", "Can Demir", "admin")

    suite = Workspace(tmp_path / "runs", [tmp_path / "suites"]).suites()["suite"]
    fields = cells_of(suite.cases[0])
    amended = "The dismissal is invalid; reinstatement follows m. 21."

    changed = editor.put(
        "/api/golden/suite/answer-1",
        json={
            "fields": {**fields, "reference answer": amended},
            "reason": "statute amended in 2025",
        },
    )
    key = answer_key("r1", "answer-1", 0)
    reviewer.post(f"/api/items/{key}/reserve")
    overruled = reviewer.post(
        f"/api/items/{key}/finish",
        json={"verdicts": [{"criterion_id": "c-statute-1", "verdict": "fail",
                            "note": "m. 18 is cited for reinstatement"}]},
    )  # fmt: skip
    log = admin.get("/api/team/audit").json()
    no_delete = admin.delete("/api/team/audit")
    by_reviewer = editor.get("/api/team/audit").json()
    refused_viewer = signed_in(server, "v@firm.example", "Viewer", "viewer").get("/api/team/audit")

    assert changed.status_code == 200, changed.text
    assert overruled.status_code == 200, overruled.text
    entries = {e["action"]: e for e in log}
    change = entries["changed"]
    assert change["by"] == "Selin Kaya" and change["reason"] == "statute amended in 2025"
    assert change["before"] != change["after"] and change["at"]
    verdict = entries["verdict"]
    assert (verdict["by"], verdict["before"], verdict["after"]) == ("Ayşe Yılmaz", "pass", "fail")
    assert verdict["reason"] == "m. 18 is cited for reinstatement"
    assert {"invited", "signed in"} <= set(entries)
    assert no_delete.status_code in (404, 405)
    assert len(by_reviewer) == len(log)
    assert refused_viewer.status_code == 403
    # Not even the database's own user removes or rewrites an entry.
    before = len(server.team.store.events())
    url = postgres
    with psycopg.connect(url) as connection:
        for statement in ("DELETE FROM events", "UPDATE events SET by = 'x'", "TRUNCATE events"):
            with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
                connection.execute(statement)  # type: ignore[arg-type]
            connection.rollback()
    with pytest.raises(DBAPIError), server.team.store.engine.begin() as connection:
        connection.execute(sa.delete(Event))
    assert len(server.team.store.events()) == before
