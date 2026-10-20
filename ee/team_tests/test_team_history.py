# SPDX-License-Identifier: Elastic-2.0
"""The team server shows a suite's history from the runs engineers push (decision 0067)."""

from pathlib import Path

from team_tests.helpers import serve, signed_in


def test_history_on_the_team_server(database: str, tmp_path: Path):
    server = serve(database, tmp_path)
    lawyer = signed_in(server, "ayse@firm.example", "Ayşe", "reviewer")

    suites = lawyer.get("/api/history").json()
    history = lawyer.get("/api/history/suite").json()

    assert [s["suite_id"] for s in suites] == ["suite"]
    assert [r["run_id"] for r in history["runs"]] == ["r1"]
    assert {s["metric"] for s in history["series"]} >= {"criteria"}
    assert signed_in(server, "x@firm.example", "X", "viewer").get("/api/history").status_code == 200
    assert lawyer.get("/api/history/missing").status_code == 404
