# SPDX-License-Identifier: Elastic-2.0
"""Alembic's entry for the team's tables, versioned apart from the core's (decision 0058)."""

from alembic import context

from casebench_ee.models import TeamBase

VERSIONS = "alembic_version_team"

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=TeamBase.metadata,
    version_table=VERSIONS,
    render_as_batch=connection.dialect.name == "sqlite",
)
with context.begin_transaction():
    context.run_migrations()
