# SPDX-License-Identifier: Elastic-2.0
"""A team server over a scored run, and browsers signed in to it, for the team server's tests."""

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from fastapi.testclient import TestClient

from casebench.suites.freeze import freeze
from casebench_ee.access import COOKIE
from casebench_ee.mail import Mailer, Outbox
from casebench_ee.server import Server, build
from tests.workbench.test_review_queue import reviewed_case, scored_run

# A Postgres server's URL, as CI sets it; without one, tests run on SQLite.
POSTGRES = os.environ.get("CASEBENCH_TEST_POSTGRES")
PUBLIC = "http://team.test"
HOST = "team.test"


@contextmanager
def fresh_postgres() -> Iterator[str]:
    """A database of its own on the Postgres server, dropped afterwards."""
    assert POSTGRES
    name = f"casebench_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(POSTGRES, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')  # type: ignore[arg-type]
    base, _, _ = POSTGRES.rpartition("/")
    try:
        yield f"{base}/{name}"
    finally:
        with psycopg.connect(POSTGRES, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')  # type: ignore[arg-type]


def serve(url: str, tmp_path: Path, mailer: Mailer | None = None, **kwargs: Any) -> Server:
    """The review queue's suite and scored run, served to a team."""
    if not (tmp_path / "runs").exists():
        suite = freeze("suite", [reviewed_case()], tmp_path / "suites" / "suite")
        scored_run(tmp_path / "runs", reviewed_case(), suite.content_hash)
    return build(
        url,
        PUBLIC,
        tmp_path / "runs",
        [tmp_path / "suites"],
        mailer=mailer if mailer is not None else Outbox(),
        **kwargs,
    )


def browser(server: Server) -> TestClient:
    return TestClient(server.app, base_url=PUBLIC)


def signed_in(server: Server, email: str, name: str, role: str) -> TestClient:
    """A browser signed in as a new person with the role."""
    user = server.team.add(email, name, role, "the test")
    client = browser(server)
    client.cookies.set(COOKIE, server.team.start(user, "test"), domain=HOST)
    return client
