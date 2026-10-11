"""The `casebench` command."""

import click

from casebench import __version__
from casebench.plugins.cli import plugin
from casebench.targets.cli import target


@click.group()
@click.version_option(__version__, prog_name="casebench")
def main() -> None:
    """Measure the legal accuracy of an AI system against court decisions."""


main.add_command(plugin)
main.add_command(target)
