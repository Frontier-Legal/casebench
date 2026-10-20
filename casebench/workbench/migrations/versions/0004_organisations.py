"""Every row carries the organisation it belongs to; existing rows are the one local one (0066).

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

LOCAL = "local"
# Each table keyed by what a person or an item is, now within an organisation: the key's
# columns and their types, as 0001 made them.
KEYED = {
    "people": {"name": 200},
    "reservations": {"item": 500},
    "drafts": {"item": 500, "person": 200},
}
LOGGED = ("events", "proposals")


def _column() -> sa.Column:
    return sa.Column("organisation", sa.String(64), nullable=False, server_default=LOCAL)


def _rekey(table: str, key: list[str]) -> None:
    """Postgres changes the key in place. SQLite cannot, so the table is copied into one with
    the new key, as SQLite's own guide to changing a table does; none of these has an index."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(f"{table}_pkey", table, type_="primary")
        op.create_primary_key(f"{table}_pkey", table, key)
        return
    old = sa.Table(table, sa.MetaData(), autoload_with=bind)
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
    copy = f"_rekeyed_{table}"
    op.create_table(copy, *columns)
    names = ", ".join(c.name for c in old.columns)
    op.execute(f"INSERT INTO {copy} ({names}) SELECT {names} FROM {table}")
    op.drop_table(table)
    op.rename_table(copy, table)


def upgrade() -> None:
    for table, widths in KEYED.items():
        op.add_column(table, _column())
        _rekey(table, ["organisation", *widths])
    for table in LOGGED:
        # A column added with a default fires no trigger, so the log stays as written.
        op.add_column(table, _column())
        op.create_index(f"{table}_by_organisation", table, ["organisation"])


def downgrade() -> None:
    for table in LOGGED:
        op.drop_index(f"{table}_by_organisation", table)
        op.drop_column(table, "organisation")
    for table, widths in KEYED.items():
        _rekey(table, list(widths))
        with op.batch_alter_table(table) as batch:
            batch.drop_column("organisation")
