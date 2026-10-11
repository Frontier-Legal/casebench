"""The `casebench` command."""

from typing import Any

import click

from casebench import __version__
from casebench.capture.cli import proxy
from casebench.config import ConfigError
from casebench.corpus.cli import corpus
from casebench.plugins.cli import plugin
from casebench.runs.cli import run
from casebench.targets.cli import target


class _Main(click.Group):
    """Turns a config problem into a one-line error instead of a traceback."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except ConfigError as error:
            raise click.ClickException(str(error)) from error


@click.group(cls=_Main)
@click.version_option(__version__, prog_name="casebench")
def main() -> None:
    """Measure the legal accuracy of an AI system against court decisions."""


main.add_command(plugin)
main.add_command(target)
main.add_command(proxy)
main.add_command(run)
main.add_command(corpus)
