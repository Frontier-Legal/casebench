"""`casebench push`, `casebench pull` and `casebench invite` (decision 0059)."""

from pathlib import Path

import click

from casebench.cloud.client import Cloud, CloudError, connect
from casebench.cloud.server_guide import GUIDE
from casebench.cloud.sync import pull, push
from casebench.config import DEFAULT_CONFIG, CasebenchConfig, load_config
from casebench.runs.cli import DEFAULT_RUNS
from casebench.workbench.access import ROLES
from casebench.workbench.sources import Workspace

CONFIG = click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
RUNS = click.option(
    "--runs-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_RUNS,
    show_default=True,
)
SUITES = click.option(
    "--suites",
    "suite_dirs",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    multiple=True,
    help="Where to look for suites; the current folder when none is given.",
)


def _cloud(config_path: Path) -> tuple[CasebenchConfig, Cloud]:
    config = load_config(config_path)
    if config.cloud is None:
        raise click.ClickException(
            f"{config_path} names no team server; name one with casebench init --team-server "
            f"URL. A team server is casebench-ee, installed on a machine lawyers reach; your "
            f"machine needs only casebench. {GUIDE} says how to run it"
        )
    try:
        return config, Cloud(connect(config.cloud, config_path.resolve().parent))
    except CloudError as failure:
        raise click.ClickException(str(failure)) from None


@click.command(name="push")
@click.argument("run_ids", nargs=-1)
@RUNS
@SUITES
@click.option(
    "--traces",
    is_flag=True,
    help="Also send each answer's steps, as ids and numbers only, never their content.",
)
@CONFIG
def push_command(
    run_ids: tuple[str, ...],
    runs_dir: Path,
    suite_dirs: tuple[Path, ...],
    traces: bool,
    config_path: Path,
) -> None:
    """Send runs and the suites they ran to the team server; every run when none is named.
    The agent, the corpus, full decision texts, the judge's replies and keys stay here."""
    config, cloud = _cloud(config_path)
    workspace = Workspace(runs_dir, list(suite_dirs) or [Path(".")])
    runs = workspace.runs()
    if run_ids:
        named = {log.info.run_id: log for log in runs}
        unknown = [r for r in run_ids if r not in named]
        if unknown:
            raise click.ClickException(f"no run {', '.join(unknown)} in {runs_dir}")
        runs = [named[r] for r in run_ids]
    if not runs:
        raise click.ClickException(f"no run in {runs_dir} to push")
    try:
        done = push(cloud, workspace, runs, traces)
    except CloudError as failure:
        raise click.ClickException(str(failure)) from None
    assert config.cloud is not None
    click.echo(
        f"pushed {len(done.runs)} runs and {len(done.suites)} suites to {config.cloud.url}"
        + (f"; {done.unchanged} were there already" if done.unchanged else "")
        + ("; steps as ids and numbers" if traces else "; no steps (add --traces to send them)")
    )
    for suite_id in done.missing_suites:
        click.echo(f"  suite {suite_id} is not under --suites, so it was not sent", err=True)


@click.command(name="pull")
@RUNS
@SUITES
@CONFIG
def pull_command(runs_dir: Path, suite_dirs: tuple[Path, ...], config_path: Path) -> None:
    """Bring back what lawyers decided on the team server: approved cases into their suites,
    and verdicts and preferences into their runs."""
    _, cloud = _cloud(config_path)
    workspace = Workspace(runs_dir, list(suite_dirs) or [Path(".")])
    try:
        done = pull(cloud, workspace)
    except CloudError as failure:
        raise click.ClickException(str(failure)) from None
    click.echo(
        f"pulled {len(done.suites)} changed suites, {done.reviews} verdicts and "
        f"{done.preferences} preferences"
    )
    for suite_id in done.suites:
        click.echo(f"  suite {suite_id} changed; the next run scores against it")


@click.command(name="invite")
@click.argument("email")
@click.option("--role", type=click.Choice(list(ROLES)), default="reviewer", show_default=True)
@click.option("--name", help="How the person is shown; the email's name when not given.")
@CONFIG
def invite_command(email: str, role: str, name: str | None, config_path: Path) -> None:
    """Invite a person to the team server by email, with a role."""
    _, cloud = _cloud(config_path)
    shown = name or email.split("@", 1)[0].replace(".", " ").title()
    try:
        made = cloud.invite(email, shown, role)
    except CloudError as failure:
        raise click.ClickException(str(failure)) from None
    waiting = made.get("waiting", 0)
    minutes = made.get("minutes", 0)
    sent = "emailed" if made.get("emailed") else "not emailed: this server sends no email"
    click.echo(f"invited {email} as {role}, {sent}; {waiting} items wait, about {minutes} minutes")
    if made.get("link"):
        click.echo(
            f"  send them this sign-in link, which works once within 15 minutes: {made['link']}"
        )
