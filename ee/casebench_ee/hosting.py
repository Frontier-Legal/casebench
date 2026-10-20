# SPDX-License-Identifier: Elastic-2.0
"""The seams a hosted service builds on: a seat check before invitations, and erasing a team.

The public server uses neither (decision 0060). In the shared service a team is one
organisation, erased alone (decision 0066).
"""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, MetaData, inspect, text

from casebench.workbench.tenancy import as_organisation
from casebench_ee import rls
from casebench_ee.folders import OrganisationWorkspace
from casebench_ee.models import User
from casebench_ee.team import Team

# Every table holding an organisation's rows, the log last so nothing refers to a person gone.
ROWS = (
    "team_sessions",
    "team_links",
    "team_keys",
    "team_handshakes",
    "team_settings",
    "team_users",
    "people",
    "reservations",
    "drafts",
    "proposals",
    "events",
)


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


def erase_organisation(team: Team, workspace: OrganisationWorkspace, organisation: str) -> None:
    """Every row of one organisation, its event log included, and its folders; the other
    organisations keep theirs. Postgres admits only that organisation's rows to the deletes,
    and lets the log be emptied only inside this transaction."""
    engine = team.store.engine
    if not rls.postgres(engine):
        raise ValueError("erasing one organisation needs Postgres; erase removes a whole server")
    with as_organisation(organisation), engine.begin() as connection:
        rls.tell(connection, erasing=True)
        for table in ROWS:
            connection.execute(
                text(f"DELETE FROM {table} WHERE organisation = :o"), {"o": organisation}
            )
        connection.execute(
            text("DELETE FROM team_organisations WHERE id = :o"), {"o": organisation}
        )
    for folder in workspace.folders(organisation):
        if folder.is_dir():
            shutil.rmtree(folder)
