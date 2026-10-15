# SPDX-License-Identifier: Elastic-2.0
"""Build the team server: the workbench with team access, the team's routes and its web app."""

import secrets
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI

from casebench.config import CasebenchConfig
from casebench.corpus.corpora import Corpora
from casebench.workbench.app import create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from casebench.workbench.trying import Limits
from casebench_ee.access import TeamAccess
from casebench_ee.hosting import SeatCheck
from casebench_ee.mail import Mailer, NoMail
from casebench_ee.oidc import Provider
from casebench_ee.routes import Settings, team_routes
from casebench_ee.sync import sync_routes
from casebench_ee.team import Team

# Letters a person reads off a log and types without confusing them.
CODE_LETTERS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def setup_code() -> str:
    groups = ("".join(secrets.choice(CODE_LETTERS) for _ in range(4)) for _ in range(3))
    return "-".join(groups)


def database_url(url: str) -> str:
    """Postgres through psycopg, whichever way the URL names it."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def static_root() -> Path | None:
    """The team build of the web app, when it was built into the package."""
    root = Path(str(resources.files("casebench_ee") / "static"))
    return root if (root / "index.html").is_file() else None


@dataclass
class Server:
    app: FastAPI
    team: Team
    setup_code: str | None
    settings: Settings = field(repr=False)


def build(
    database: str,
    public_url: str,
    runs_dir: Path,
    suite_dirs: list[Path],
    config: CasebenchConfig | None = None,
    mailer: Mailer | None = None,
    providers: dict[str, Provider] | None = None,
    hosts: list[str] | None = None,
    seats: SeatCheck | None = None,
) -> Server:
    """A team with no one yet gets a one-time setup code, which the caller prints."""
    store = Store(database_url(database))
    runs_dir.mkdir(parents=True, exist_ok=True)
    for folder in suite_dirs:
        folder.mkdir(parents=True, exist_ok=True)
    team = Team(store)
    code = setup_code() if team.setup_needed() else None
    settings = Settings(public_url=public_url, setup_code=code, config=config)
    corpora = Corpora(config.corpora) if config and config.corpora else None
    workspace = Workspace(runs_dir, suite_dirs, corpora, config.agent_models if config else [])
    configured = config.workbench.try_daily_limit_usd if config and config.workbench else None

    def limits() -> Limits:
        """The admin's limits; until the admin sets a team limit, casebench.yaml's."""
        found = team.limits()
        return Limits(
            team=found.team if found.team is not None else configured, person=found.person
        )

    app = create_app(
        workspace,
        store,
        hosts or [urlsplit(public_url).netloc],
        static=static_root(),
        config=config,
        access=TeamAccess(team),
        routers=[
            team_routes(team, mailer or NoMail(), providers or {}, settings, workspace, seats),
            sync_routes(workspace, store),
        ],
        limits=limits,
    )
    return Server(app=app, team=team, setup_code=code, settings=settings)
