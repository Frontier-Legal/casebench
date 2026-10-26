"""Two workbenches started at the same moment on a project with no database both start, and
leave one database with the newest schema (decision 0050)."""

import multiprocessing
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

from alembic.script import ScriptDirectory

from casebench.workbench.store import Store, url_for

# A ceiling, not a measurement: starting Python and migrating an empty database takes a few
# seconds on a CI runner.
STARTED_WITHIN_S = 60.0
STARTED = "started"
# Two starts are enough for the second to find the tables the first is creating.
WORKBENCHES = 2


def _start(url: str, together: Any, said: Any) -> None:
    """One `casebench ui` opening its store, released at the same moment as the other."""
    together.wait()
    try:
        Store(url)
        said.put(STARTED)
    except Exception as error:
        said.put(f"{type(error).__name__}: {error}")


def test_two_workbenches_started_at_once_on_a_new_project_both_start(tmp_path: Path):
    database = tmp_path / ".casebench" / "casebench.db"
    database.parent.mkdir()
    spawned = multiprocessing.get_context("spawn")
    together, said = spawned.Barrier(WORKBENCHES), spawned.Queue()
    starts = [
        spawned.Process(target=_start, args=(url_for(database), together, said))
        for _ in range(WORKBENCHES)
    ]

    for start in starts:
        start.start()
    outcomes = [said.get(timeout=STARTED_WITHIN_S) for _ in starts]
    for start in starts:
        start.join(STARTED_WITHIN_S)

    assert outcomes == [STARTED] * WORKBENCHES
    with sqlite3.connect(database) as connection:
        (version,) = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    migrations = str(resources.files("casebench.workbench") / "migrations")
    assert version == ScriptDirectory(migrations).get_current_head()
