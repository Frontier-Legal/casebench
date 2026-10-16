# SPDX-License-Identifier: Elastic-2.0
"""The seams a hosted service builds on: a seat check before invitations, and erasing a team.

The public server uses neither (decision 0060).
"""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, MetaData, inspect, text

from casebench_ee.models import User
from casebench_ee.team import Team


@dataclass(frozen=True)
class Seats:
    """How many seats the team pays for, and where more are added."""

    paid: int
    add_at: str


# Given the team, its seats; the hosted service passes one, the public server none.
SeatCheck = Callable[[Team], Seats]


def members(team: Team) -> list[User]:
    return [u for u in team.users() if u.active]


def erase(engine: Engine, folders: list[Path]) -> list[str]:
    """Every table in the team's database, with the event log's guard, and everything in its
    run and suite folders. Returns the tables removed."""
    tables = inspect(engine).get_table_names()
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(text("DROP TRIGGER IF EXISTS events_append_only ON events"))
            connection.execute(text("DROP FUNCTION IF EXISTS events_append_only()"))
        metadata = MetaData()
        metadata.reflect(bind=connection)
        metadata.drop_all(bind=connection)
    for folder in folders:
        if folder.is_dir():
            for child in folder.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    return sorted(tables)
