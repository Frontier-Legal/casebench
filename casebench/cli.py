"""The `casebench` command."""

from typing import Any

import click

from casebench import __version__
from casebench.capture.cli import proxy
from casebench.cases.cli import case_group
from casebench.config import ConfigError
from casebench.corpus.cli import corpus
from casebench.extract.cli import extract_command
from casebench.formats.schema_cli import schema
from casebench.formats.validate_cli import validate_command
from casebench.formats.version import UnreadableFormat
from casebench.plugins.cli import plugin
from casebench.report.cli import compare_command, report_command
from casebench.runs.cli import run
from casebench.setup.check_cli import check_command
from casebench.setup.guide_cli import guide_command
from casebench.setup.init_cli import init_command
from casebench.setup.keys_cli import keys_command
from casebench.suites.cli import generate_command
from casebench.targets.cli import target


class _Main(click.Group):
    """Turns a config problem or an unreadable format into a one-line error, not a traceback."""

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except (ConfigError, UnreadableFormat) as error:
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
main.add_command(extract_command)
main.add_command(generate_command)
main.add_command(case_group)
main.add_command(report_command)
main.add_command(compare_command)
main.add_command(init_command)
main.add_command(check_command)
main.add_command(keys_command)
main.add_command(guide_command)
main.add_command(schema)
main.add_command(validate_command)
