# SPDX-License-Identifier: Elastic-2.0
"""Postgres keeps organisations apart: every transaction is told whom it is for (decision 0066).

Row-level security, set up by migration t0002, then admits only that organisation's rows. A
sign-in, which finds a session, link, key or person by its token or email alone, may read the
sign-in tables across organisations, and nothing else.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from sqlalchemy import Connection, Engine, event, text
from sqlalchemy.orm import sessionmaker

from casebench.workbench.tenancy import current

_SIGNING_IN: ContextVar[bool] = ContextVar("casebench_signing_in", default=False)
TOLD = (
    "SELECT set_config('casebench.organisation', %s, true), "
    "set_config('casebench.signing_in', %s, true), set_config('casebench.erasing', %s, true)"
)


def postgres(engine: Engine) -> bool:
    return engine.dialect.name == "postgresql"


@contextmanager
def signing_in() -> Iterator[None]:
    """Reads made inside find a sign-in's rows whichever organisation holds them."""
    token = _SIGNING_IN.set(True)
    try:
        yield
    finally:
        _SIGNING_IN.reset(token)


def tell(connection: Connection, erasing: bool = False) -> None:
    """For this transaction only: `set_config` with `true` is `SET LOCAL` with parameters."""
    on = ("off", "on")
    connection.exec_driver_sql(TOLD, (current(), on[_SIGNING_IN.get()], on[erasing]))


def scope(engine: Engine, *makers: sessionmaker[Any]) -> None:
    """Every session the makers open tells Postgres whom its transaction is for."""
    if not postgres(engine):
        return
    for maker in makers:
        event.listen(maker, "after_begin", lambda _session, _tx, connection: tell(connection))


def bypassed(engine: Engine) -> bool:
    """Whether the server's database role skips row-level security: a superuser does, and a
    role with BYPASSRLS, so organisations would not be kept apart."""
    if not postgres(engine):
        return True
    with engine.connect() as connection:
        query = "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
        return bool(connection.execute(text(query)).scalar())
