"""`casebench demo`: run the bundled project and open the workbench on its failures."""

import contextlib
import shutil
import tempfile
from pathlib import Path

import click

from casebench.demo import PROJECT, write_config
from casebench.judge.memo import MEMO_FILE
from casebench.runs.cli import run
from casebench.runs.log import RunInfo, RunLog
from casebench.suites.freeze import load
from casebench.workbench.cli import PORT, ui_command
from casebench.workbench.store import url_for

RUN_ID = "demo"


@click.command(name="demo")
@click.option(
    "--dir",
    "folder",
    type=click.Path(file_okay=False, path_type=Path),
    help="Where to keep the demo; a new temporary folder when not given.",
)
@click.option("--no-serve", is_flag=True, help="Stop after the run; do not open the workbench.")
@click.option("--port", type=click.IntRange(1024, 65535), default=PORT, show_default=True)
@click.pass_context
def demo_command(ctx: click.Context, folder: Path | None, no_serve: bool, port: int) -> None:
    """Run a bundled suite with no key and no data, and open the workbench. Like every run,
    it reads two public price lists; nothing of yours is sent, and no model is asked."""
    if folder is None:
        folder = Path(tempfile.mkdtemp(prefix="casebench-demo-"))
    elif folder.exists() and any(folder.iterdir()):
        raise click.ClickException(f"{folder} is not empty; name a new folder with --dir")
    # Resolved here, since a relative path would be read again inside the folder itself.
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    # Everything the demo writes, its corpus cache included, stays in its own folder.
    with contextlib.chdir(folder):
        _demo(ctx, folder, no_serve, port)


def _demo(ctx: click.Context, folder: Path, no_serve: bool, port: int) -> None:
    click.echo(
        "The demo's cases, court decisions and answers are written for it: none is a real "
        "decision or legal advice. Its judge's replies are kept with it, so no model is asked."
    )
    for part in ("suite", "corpus"):
        shutil.copytree(PROJECT / part, folder / part)
    config_path = write_config(folder, folder)
    runs_dir = folder / "runs"
    manifest, _ = load(folder / "suite")
    log = RunLog.create(
        runs_dir / RUN_ID,
        RunInfo(
            run_id=RUN_ID,
            suite_id=manifest.suite_id,
            suite_hash=manifest.content_hash,
            target="python",
        ),
    )
    shutil.copyfile(PROJECT / MEMO_FILE, log.folder / MEMO_FILE)
    ctx.invoke(
        run,
        suite_dir=folder / "suite",
        config_path=config_path,
        python=None,
        max_concurrency=None,
        run_id=RUN_ID,
        runs_dir=runs_dir,
        no_capture=True,
        dry_run=False,
        commit=None,
    )
    if no_serve:
        click.echo(f"the demo is in {folder}")
        return
    click.echo("failed answers come first in the review queue, each beside its evidence")
    ctx.invoke(
        ui_command,
        runs_dir=runs_dir,
        suite_dirs=(folder / "suite",),
        config_path=config_path,
        database=url_for(folder / "casebench.db"),
        port=port,
        role=None,
        no_open=False,
    )
