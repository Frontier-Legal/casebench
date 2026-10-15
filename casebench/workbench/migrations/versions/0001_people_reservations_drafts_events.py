"""People, reservations, drafts and the event log.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("name", sa.String(200), primary_key=True),
        sa.Column("view", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "reservations",
        sa.Column("item", sa.String(500), primary_key=True),
        sa.Column("person", sa.String(200), nullable=False),
        sa.Column("until", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "drafts",
        sa.Column("item", sa.String(500), primary_key=True),
        sa.Column("person", sa.String(200), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("by", sa.String(200), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("item", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("events_by_item", "events", ["item"])


def downgrade() -> None:
    op.drop_index("events_by_item", "events")
    for table in ("events", "drafts", "reservations", "people"):
        op.drop_table(table)
