# SPDX-License-Identifier: Elastic-2.0
"""One shared server keeps its organisations apart in the database itself (decision 0066)."""

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest

from casebench.suites.freeze import freeze
from casebench.workbench.items import answer_key
from casebench.workbench.tenancy import LOCAL, as_organisation
from casebench_ee.access import COOKIE
from casebench_ee.hosting import erase_organisation
from casebench_ee.server import Server
from casebench_ee.team import TeamError
from team_tests.helpers import HOST, POSTGRES, browser, serve, signed_in
from tests.workbench.test_review_queue import reviewed_case, scored_run

ITEM = answer_key("r1", reviewed_case().id, 0)


def second_firm(server: Server) -> tuple[str, object]:
    """Another organisation with a run of the same id, r1, and its admin signed in."""
    firm = server.team.add_organisation("Second firm")
    assert server.workspace is not None
    folder = server.workspace.folder(firm.id)
    suite = freeze("suite", [reviewed_case()], folder / "suites" / "suite")
    scored_run(folder / "runs", reviewed_case(), suite.content_hash)
    with as_organisation(firm.id):
        admin = signed_in(server, "deniz@second.example", "Deniz", "admin")
    return firm.id, admin


def as_owner(url: str) -> str:
    """The service's database, reached as the server's superuser, which sees every row."""
    assert POSTGRES
    return urlunsplit(urlsplit(POSTGRES)._replace(path=urlsplit(url).path))


def test_tenants_are_isolated(service: str, tmp_path: Path):
    server = serve(service, tmp_path)
    first = signed_in(server, "selin@first.example", "Selin", "admin")
    _, second = second_firm(server)
    # A run only the first firm has.
    (tmp_path / "runs" / "r1").rename(tmp_path / "runs" / "first-only")
    suite = freeze("suite", [reviewed_case()], tmp_path / "suites" / "suite")
    scored_run(tmp_path / "runs", reviewed_case(), suite.content_hash)
    own = first.get("/api/runs/first-only/report")
    theirs = second.get("/api/runs/first-only/report")  # type: ignore[attr-defined]

    # The same run id, r1, in both: each reserves its own answer, and neither waits.
    held = second.post(f"/api/items/{ITEM}/reserve")  # type: ignore[attr-defined]
    also = first.post(f"/api/items/{ITEM}/reserve")
    people = [u["email"] for u in first.get("/api/team/users").json()]
    others = [u["email"] for u in second.get("/api/team/users").json()]  # type: ignore[attr-defined]
    audit = first.get("/api/team/audit").json()

    assert own.status_code == 200
    assert theirs.status_code == 404
    assert held.json()["held_by"] == "Deniz"
    assert also.status_code == 200 and also.json()["held_by"] == "Selin"
    assert people == ["selin@first.example"]
    assert others == ["deniz@second.example"]
    assert not any("deniz" in str(event) for event in audit)
    # A query that names no organisation gets no row of any.
    with psycopg.connect(service.replace("+psycopg", "")) as raw:
        assert raw.execute("SELECT count(*) FROM team_users").fetchone() == (0,)
        raw.execute("SELECT set_config('casebench.organisation', %s, false)", (LOCAL,))
        assert raw.execute("SELECT email FROM team_users").fetchall() == [("selin@first.example",)]


def test_a_person_signs_in_to_their_own_organisation(service: str, tmp_path: Path):
    server = serve(service, tmp_path)
    signed_in(server, "selin@first.example", "Selin", "admin")
    firm = server.team.add_organisation("Second firm")
    with as_organisation(firm.id):
        user = server.team.add("can@second.example", "Can", "reviewer", "the test")
        token = server.team.link(user)

    client = browser(server)
    opened = client.get(f"/auth/link?token={token}", follow_redirects=False)
    me = client.get("/api/me")

    assert opened.status_code in (302, 303, 307), opened.text
    assert client.cookies.get(COOKIE, domain=HOST)
    assert me.json()["name"] == "Can"
    # Its session row is the second firm's, so the first firm's people never see it.
    with psycopg.connect(as_owner(service)) as raw:
        found = raw.execute(
            "SELECT DISTINCT organisation FROM team_sessions WHERE user_id = %s", (user.id,)
        )
        assert found.fetchall() == [(firm.id,)]


def test_erasing_one_organisation_leaves_the_others(service: str, tmp_path: Path):
    server = serve(service, tmp_path)
    first = signed_in(server, "selin@first.example", "Selin", "admin")
    firm, second = second_firm(server)
    second.post(f"/api/items/{ITEM}/reserve")  # type: ignore[attr-defined]
    assert server.workspace is not None

    erase_organisation(server.team, server.workspace, firm)

    assert not server.workspace.folder(firm).exists()
    assert second.get("/api/me").status_code == 401  # type: ignore[attr-defined]
    assert [u["email"] for u in first.get("/api/team/users").json()] == ["selin@first.example"]
    assert first.get(f"/api/items/{ITEM}").status_code == 200
    with psycopg.connect(as_owner(service)) as raw:
        for table in ("team_users", "team_sessions", "reservations", "events"):
            left = raw.execute(f"SELECT count(*) FROM {table} WHERE organisation = %s", (firm,))  # type: ignore[arg-type]
            assert left.fetchone() == (0,), table
        assert raw.execute("SELECT id FROM team_organisations").fetchall() == [(LOCAL,)]
        # Outside erasing, the event log still refuses a delete.
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            raw.execute("DELETE FROM events")


def test_a_server_that_cannot_keep_organisations_apart_has_one(database: str, tmp_path: Path):
    """SQLite, or Postgres as a superuser, as a self-hosted server may run."""
    server = serve(database, tmp_path)
    with pytest.raises(TeamError, match="does not keep organisations apart"):
        server.team.add_organisation("Second firm")
    assert [o.id for o in server.team.organisations()] == [LOCAL]
