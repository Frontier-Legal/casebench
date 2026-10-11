"""`casebench check`: every check the config calls for, on the machine that will run it."""

from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, load_config
from casebench.corpus.check import SAMPLE_SIZE
from casebench.setup.checks import Status, live, offline


@click.command(name="check")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option(
    "--query",
    "queries",
    multiple=True,
    help="A search that finds documents, for a store that cannot list them.",
)
@click.option("--size", type=click.IntRange(min=1), default=SAMPLE_SIZE, show_default=True)
def check_command(config_path: Path, queries: tuple[str, ...], size: int) -> None:
    """Check the corpus, the target and the judge from here; fail if any does not pass."""
    config = load_config(config_path)
    checks = offline(config)
    if not checks:
        checks = live(config, list(queries), size)
    for item in checks:
        click.echo(item.line())
    if any(item.status is not Status.PASSED for item in checks):
        raise SystemExit(1)
