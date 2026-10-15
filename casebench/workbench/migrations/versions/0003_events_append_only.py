"""The event log refuses any update or delete, in the database itself (decision 0058).

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

REFUSED = "the event log is append-only"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER events_no_{action.lower()} BEFORE {action} ON events "
                f"BEGIN SELECT RAISE(ABORT, '{REFUSED}'); END"
            )
    elif dialect == "postgresql":
        op.execute(
            "CREATE FUNCTION events_append_only() RETURNS trigger LANGUAGE plpgsql AS "
            f"$$ BEGIN RAISE EXCEPTION '{REFUSED}'; END $$"
        )
        op.execute(
            "CREATE TRIGGER events_append_only BEFORE UPDATE OR DELETE OR TRUNCATE ON events "
            "FOR EACH STATEMENT EXECUTE FUNCTION events_append_only()"
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER events_no_update")
        op.execute("DROP TRIGGER events_no_delete")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER events_append_only ON events")
        op.execute("DROP FUNCTION events_append_only()")
