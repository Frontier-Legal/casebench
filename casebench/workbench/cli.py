"""`casebench ui`: the workbench on this machine, with no login (decision 0050)."""

import webbrowser
from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, load_config
from casebench.corpus.corpora import Corpora
from casebench.runs.cli import DEFAULT_RUNS
from casebench.workbench.app import ENGINEER, REVIEWER, create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import DEFAULT_DATABASE, Store, url_for

LOOPBACK = "127.0.0.1"
PORT = 7462


@click.command(name="ui")
@click.option(
    "--runs-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_RUNS,
    show_default=True,
)
@click.option(
    "--suites",
    "suite_dirs",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    multiple=True,
    help="Where to look for suites; the current folder when none is given.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
    help="Its corpus shows each passage in its decision.",
)
@click.option("--database", help="A database URL; SQLite under .casebench/ when not given.")
@click.option("--port", type=click.IntRange(1024, 65535), default=PORT, show_default=True)
@click.option(
    "--role",
    type=click.Choice([REVIEWER, ENGINEER]),
    help="reviewer serves the review view only, with no way to show engineering detail.",
)
@click.option("--no-open", is_flag=True, help="Do not open the browser.")
def ui_command(
    runs_dir: Path,
    suite_dirs: tuple[Path, ...],
    config_path: Path,
    database: str | None,
    port: int,
    role: str | None,
    no_open: bool,
) -> None:
    """Open the review queue: answers to review and court drafts to approve."""
    import uvicorn

    config = load_config(config_path) if config_path.is_file() else None
    corpora = Corpora(config.corpora) if config and config.corpora else None
    agent_models = config.agent_models if config else []
    workspace = Workspace(runs_dir, list(suite_dirs) or [Path(".")], corpora, agent_models)
    store = Store(database or url_for(DEFAULT_DATABASE))
    hosts = [f"{LOOPBACK}:{port}", f"localhost:{port}"]
    app = create_app(workspace, store, hosts, role)
    url = f"http://{LOOPBACK}:{port}/"
    click.echo(f"the workbench is at {url}; press Ctrl+C to stop it")
    if not no_open:
        webbrowser.open(url)
    uvicorn.run(app, host=LOOPBACK, port=port, log_level="warning")
