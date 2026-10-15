"""Alembic's entry: migrate the connection the workbench hands over (decision 0050)."""

from alembic import context

from casebench.workbench.store import Base

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    render_as_batch=connection.dialect.name == "sqlite",
)
with context.begin_transaction():
    context.run_migrations()
