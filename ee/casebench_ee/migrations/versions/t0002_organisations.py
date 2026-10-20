# SPDX-License-Identifier: Elastic-2.0
"""Organisations, a column naming one on every row, and Postgres keeping them apart (0066).

Revision ID: t0002
Revises: t0001
"""

import sqlalchemy as sa
from alembic import op

revision = "t0002"
down_revision = "t0001"
branch_labels = None
depends_on = None

LOCAL = "local"
SIGN_IN = ("team_users", "team_sessions", "team_links", "team_keys", "team_handshakes")
# Every table holding an organisation's rows, the workbench's and the team's.
STRICT = ("people", "reservations", "drafts", "events", "proposals", "team_settings")
# The organisation each transaction is for, set by the server before its first query.
CURRENT = "current_setting('casebench.organisation', true)"
# Signing in reads a session, a link, a key or a person by its token or email alone.
SIGNING_IN = "current_setting('casebench.signing_in', true) = 'on'"
REFUSED = "the event log is append-only"


def _column() -> sa.Column:
    return sa.Column("organisation", sa.String(64), nullable=False, server_default=LOCAL)


def _rekey_settings(key: list[str]) -> None:
    """Postgres changes the key in place; SQLite copies the table, as its guide says to."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("team_settings_pkey", "team_settings", type_="primary")
        op.create_primary_key("team_settings_pkey", "team_settings", key)
        return
    old = sa.Table("team_settings", sa.MetaData(), autoload_with=bind)
    columns = [
        sa.Column(
            c.name,
            c.type,
            nullable=c.nullable,
            primary_key=c.name in key,
            server_default=c.server_default.arg if c.server_default is not None else None,  # type: ignore[attr-defined]
        )
        for c in old.columns
    ]
    op.create_table("_rekeyed_team_settings", *columns)
    names = ", ".join(c.name for c in old.columns)
    op.execute(f"INSERT INTO _rekeyed_team_settings ({names}) SELECT {names} FROM team_settings")
    op.drop_table("team_settings")
    op.rename_table("_rekeyed_team_settings", "team_settings")


def _keep_apart() -> None:
    """Each table admits only the rows of the transaction's organisation, its owner too; the
    sign-in tables can also be read while signing in, and the log emptied while erasing."""
    for table in (*STRICT, *SIGN_IN, "team_organisations"):
        column = "id" if table == "team_organisations" else "organisation"
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY organisation ON {table} "
            f"USING ({column} = {CURRENT}) WITH CHECK ({column} = {CURRENT})"
        )
    for table in SIGN_IN:
        op.execute(f"CREATE POLICY signing_in ON {table} FOR SELECT USING ({SIGNING_IN})")
    op.execute(
        "CREATE OR REPLACE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN IF TG_OP = 'DELETE' AND current_setting('casebench.erasing', true) = 'on' "
        f"THEN RETURN NULL; END IF; RAISE EXCEPTION '{REFUSED}'; END $$"
    )


def upgrade() -> None:
    op.create_table(
        "team_organisations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO team_organisations (id, name, created_at) "
        f"VALUES ('{LOCAL}', 'This server', CURRENT_TIMESTAMP)"
    )
    for table in SIGN_IN:
        op.add_column(table, _column())
    op.add_column("team_settings", _column())
    _rekey_settings(["organisation", "name"])
    if op.get_bind().dialect.name == "postgresql":
        _keep_apart()


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in (*STRICT, *SIGN_IN, "team_organisations"):
            op.execute(f"DROP POLICY IF EXISTS organisation ON {table}")
            op.execute(f"DROP POLICY IF EXISTS signing_in ON {table}")
            op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(
            "CREATE OR REPLACE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql "
            f"AS $$ BEGIN RAISE EXCEPTION '{REFUSED}'; END $$"
        )
    _rekey_settings(["name"])
    with op.batch_alter_table("team_settings") as batch:
        batch.drop_column("organisation")
    for table in SIGN_IN:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("organisation")
    op.drop_table("team_organisations")
