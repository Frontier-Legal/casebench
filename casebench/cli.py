"""The `casebench` command."""

import click

from casebench import __version__


@click.group()
@click.version_option(__version__, prog_name="casebench")
def main() -> None:
    """Measure the legal accuracy of an AI system against court decisions."""
