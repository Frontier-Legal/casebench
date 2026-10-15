# SPDX-License-Identifier: Elastic-2.0
"""A fresh database for each test: Postgres when CASEBENCH_TEST_POSTGRES names a server, as in
CI, else SQLite."""

from collections.abc import Iterator
from pathlib import Path

import pytest

from team_tests.helpers import POSTGRES, fresh_postgres


@pytest.fixture
def postgres() -> Iterator[str]:
    """Postgres, as a team deploys it; skipped where there is none."""
    if not POSTGRES:
        pytest.skip("needs Postgres: set CASEBENCH_TEST_POSTGRES to a server's URL")
    with fresh_postgres() as url:
        yield url


@pytest.fixture
def database(tmp_path: Path) -> Iterator[str]:
    """Postgres when there is one, else a SQLite file."""
    if not POSTGRES:
        yield f"sqlite:///{tmp_path / 'team.db'}"
        return
    with fresh_postgres() as url:
        yield url
