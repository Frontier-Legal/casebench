# SPDX-License-Identifier: Elastic-2.0
"""What the hosted service builds on, and that the public server needs none of it (0060)."""

import ast
import re
import sys
from pathlib import Path

from click.testing import CliRunner
from sqlalchemy import create_engine, inspect

from casebench_ee.cli import main as team_cli
from casebench_ee.hosting import Seats
from casebench_ee.server import database_url
from team_tests.helpers import serve, signed_in

EE = Path(__file__).parents[1] / "casebench_ee"
# What ee/pyproject.toml and the core bring, by the name each is imported as.
DEPENDENCIES = {
    "alembic",
    "click",
    "fastapi",
    "httpx2",
    "jwt",
    "psycopg",
    "pydantic",
    "sqlalchemy",
    "uvicorn",
}


def test_invite_consumes_a_seat(database: str, tmp_path: Path):
    server = serve(database, tmp_path, seats=lambda team: Seats(5, "https://casebench.app/billing"))
    admin = signed_in(server, "selin@firm.example", "Selin", "admin")
    for n in range(4):
        made = admin.post(
            "/api/team/users",
            json={"email": f"l{n}@firm.example", "name": f"L{n}", "role": "reviewer"},
        )
        assert made.status_code == 200, made.text

    sixth = admin.post(
        "/api/team/users", json={"email": "six@firm.example", "name": "Six", "role": "reviewer"}
    )

    assert sixth.status_code == 402
    assert "all 5 seats are taken by 5 members" in sixth.json()["detail"]
    assert "https://casebench.app/billing" in sixth.json()["detail"]
    assert server.team.by_email("six@firm.example") is None


def test_delete_everything(postgres: str, tmp_path: Path):
    server = serve(postgres, tmp_path)
    signed_in(server, "selin@firm.example", "Selin", "admin")
    name = postgres.rsplit("/", 1)[1]

    refused = CliRunner().invoke(team_cli, ["erase", "--database", postgres, "--confirm", "other"])
    erased = CliRunner().invoke(
        team_cli,
        ["erase", "--database", postgres, "--runs-dir", str(tmp_path / "runs"), "--suites",
         str(tmp_path / "suites"), "--confirm", name],
    )  # fmt: skip

    assert refused.exit_code != 0 and f"--confirm {name}" in refused.output
    assert erased.exit_code == 0, erased.output
    assert inspect(create_engine(database_url(postgres))).get_table_names() == []
    assert list((tmp_path / "runs").iterdir()) == [] and list((tmp_path / "suites").iterdir()) == []


def test_public_app_runs_without_cloud_code(database: str, tmp_path: Path):
    server = serve(database, tmp_path)
    admin = signed_in(server, "selin@firm.example", "Selin", "admin")
    paths = [getattr(route, "path", "") for route in server.app.routes]
    imported = {
        alias.name.split(".")[0]
        for path in EE.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")]
        )
    }

    # No seat check: invitations are not counted.
    for n in range(8):
        made = admin.post(
            "/api/team/users",
            json={"email": f"p{n}@firm.example", "name": f"P{n}", "role": "viewer"},
        )
        assert made.status_code == 200
    assert not [p for p in paths if re.search(r"sign-?up|billing|seat|organi[sz]ation|tenant", p)]
    # It imports the standard library, the core and its declared dependencies, nothing else.
    allowed = set(sys.stdlib_module_names) | {"casebench", "casebench_ee", *DEPENDENCIES}
    assert imported - {""} <= allowed, imported - allowed
