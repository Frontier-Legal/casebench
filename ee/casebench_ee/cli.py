# SPDX-License-Identifier: Elastic-2.0
"""`casebench-team serve`: the team server, configured by options or by the environment."""

import os
from pathlib import Path

import click

from casebench.config import load_config
from casebench_ee import hosting
from casebench_ee.mail import NoMail, Smtp
from casebench_ee.oidc import GOOGLE, MICROSOFT, Provider
from casebench_ee.server import build, database_url


def env(name: str) -> str | None:
    return os.environ.get(f"CASEBENCH_{name}") or None


def mailer():
    """SMTP when CASEBENCH_SMTP_HOST is set; the password is read from the environment only."""
    host = env("SMTP_HOST")
    if host is None:
        return NoMail()
    security = env("SMTP_SECURITY") or "starttls"
    port = int(env("SMTP_PORT") or (465 if security == "tls" else 587))
    return Smtp(
        host=host,
        port=port,
        sender=env("SMTP_FROM") or f"casebench@{host}",
        username=env("SMTP_USERNAME"),
        password=env("SMTP_PASSWORD"),
        security=security,
    )


def providers() -> dict[str, Provider]:
    found = {}
    for name, discovery in (("google", GOOGLE), ("microsoft", MICROSOFT)):
        client, secret = env(f"{name.upper()}_CLIENT_ID"), env(f"{name.upper()}_CLIENT_SECRET")
        if client and secret:
            found[name] = Provider(name, client, secret, discovery)
    return found


@click.group()
def main() -> None:
    """Casebench's team server (decision 0058)."""


@main.command()
@click.option("--database", envvar="CASEBENCH_DATABASE_URL", required=True)
@click.option(
    "--runs-dir", envvar="CASEBENCH_RUNS", type=click.Path(file_okay=False, path_type=Path)
)
@click.option("--suites", envvar="CASEBENCH_SUITES", default="")
@click.option(
    "--confirm", help="The database's name, typed back: what is erased cannot be restored."
)
def erase(database: str, runs_dir: Path | None, suites: str, confirm: str | None) -> None:
    """Remove everything this team has: its tables, runs and suites (decision 0060)."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    url = make_url(database_url(database))
    name = url.database or ""
    if confirm != name:
        raise click.ClickException(f"to erase it, pass --confirm {name}")
    folders = ([runs_dir] if runs_dir else []) + [Path(p) for p in suites.split(os.pathsep) if p]
    removed = hosting.erase(create_engine(url), folders)
    click.echo(f"erased {len(removed)} tables and {len(folders)} folders' contents of {name}")


@main.command()
@click.option(
    "--database",
    envvar="CASEBENCH_DATABASE_URL",
    default="sqlite:///.casebench/team.db",
    show_default=True,
    help="Postgres for a team, such as postgresql://user@host/db.",
)
@click.option(
    "--public-url",
    envvar="CASEBENCH_PUBLIC_URL",
    default="http://127.0.0.1:8080",
    show_default=True,
    help="Where people open the app; links in emails point here.",
)
@click.option("--host", envvar="CASEBENCH_HOST", default="127.0.0.1", show_default=True)
@click.option("--port", envvar="CASEBENCH_PORT", default=8080, type=int, show_default=True)
@click.option(
    "--runs-dir",
    envvar="CASEBENCH_RUNS",
    default=".casebench/runs",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
)
@click.option(
    "--suites",
    envvar="CASEBENCH_SUITES",
    default=".",
    show_default=True,
    help="Folders to look for suites in, separated by the path separator.",
)
@click.option(
    "--config",
    "config_path",
    envvar="CASEBENCH_CONFIG",
    default="casebench.yaml",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
)
def serve(
    database: str,
    public_url: str,
    host: str,
    port: int,
    runs_dir: Path,
    suites: str,
    config_path: Path,
) -> None:
    """Serve the workbench to a team. A team with no one yet prints a one-time setup code."""
    import uvicorn

    config = load_config(config_path) if config_path.is_file() else None
    server = build(
        database,
        public_url,
        runs_dir,
        [Path(p) for p in suites.split(os.pathsep) if p],
        config,
        mailer(),
        providers(),
    )
    if server.setup_code:
        click.echo(
            f"No one is in this team yet. Open {public_url} and enter the setup code "
            f"{server.setup_code} to create the first admin.",
            err=True,
        )
    click.echo(f"the team server is at {public_url}", err=True)
    uvicorn.run(server.app, host=host, port=port, log_level="info", proxy_headers=True)
