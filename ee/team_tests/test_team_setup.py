# SPDX-License-Identifier: Elastic-2.0
"""The first admin is set up with the code in the server's log, and no default password."""

from pathlib import Path

from team_tests.helpers import browser, serve

STRONG = "torn-ledger-41-maple"


def test_first_admin_at_setup(postgres: str, tmp_path: Path):
    server = serve(postgres, tmp_path)
    app = browser(server)
    form = {"name": "Selin Kaya", "email": "selin@firm.example", "password": STRONG}

    before = app.get("/api/team/status").json()
    unsigned = app.get("/api/queue")
    wrong_code = app.post("/api/team/setup", json={**form, "code": "AAAA-BBBB-CCCC"})
    defaults = {
        password: app.post(
            "/api/team/setup", json={**form, "code": server.setup_code, "password": password}
        ).status_code
        for password in (
            "admin",
            "changeme",
            "password12345",
            "adminadminadmin",
            "selin-2026-maple",
        )
    }
    made = app.post("/api/team/setup", json={**form, "code": server.setup_code})
    me = app.get("/api/me").json()
    again = app.post("/api/team/setup", json={**form, "code": "anything"})
    # The server starts again on the same database: setup stays closed, the password works.
    restarted = serve(postgres, tmp_path)
    returning = browser(restarted)
    signed = returning.post(
        "/api/team/signin/password", json={"email": "Selin@Firm.Example", "password": STRONG}
    )

    assert before["setup_needed"] is True and server.setup_code
    assert unsigned.status_code == 401
    assert wrong_code.status_code == 403
    assert set(defaults.values()) == {422}
    assert made.status_code == 200, made.text
    assert (me["name"], me["role"]) == ("Selin Kaya", "admin")
    assert "admin" in me["can"]
    assert again.status_code == 409
    assert restarted.setup_code is None
    assert returning.get("/api/team/status").json()["setup_needed"] is False
    assert signed.status_code == 200, signed.text
    assert returning.get("/api/me").json()["role"] == "admin"
    [stored] = restarted.team.users()
    assert (
        stored.password and STRONG not in stored.password and stored.password.startswith("scrypt$")
    )


def test_a_wrong_password_locks_out_after_five_tries(database: str, tmp_path: Path):
    server = serve(database, tmp_path)
    app = browser(server)
    app.post(
        "/api/team/setup",
        json={"code": server.setup_code, "name": "Selin", "email": "selin@firm.example",
              "password": STRONG},
    )  # fmt: skip
    other = browser(server)

    tries = [
        other.post(
            "/api/team/signin/password", json={"email": "selin@firm.example", "password": "nope"}
        ).status_code
        for _ in range(6)
    ]
    late = other.post(
        "/api/team/signin/password", json={"email": "selin@firm.example", "password": STRONG}
    )

    assert tries == [401] * 5 + [429]
    assert late.status_code == 429
