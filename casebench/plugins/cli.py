"""`casebench plugin`: list the plugin kinds, scaffold a plugin, test one."""

from pathlib import Path

import click

from casebench.plugins import conformance, scaffold
from casebench.plugins.kinds import BY_NAME, KINDS, kind_named


@click.group()
def plugin() -> None:
    """Add a jurisdiction, a data provider, a model provider or any other plugin."""


@plugin.command()
def kinds() -> None:
    """Every plugin kind: its entry-point group, its interface and its conformance command."""
    for kind in KINDS:
        click.echo(f"{kind.name}")
        click.echo(f"  entry points  {kind.group}")
        click.echo(f"  interface     {kind.interface_path}")
        click.echo(f"  conformance   {kind.conformance_command}")
        if kind.figure:
            click.echo(f"  measures      {kind.figure}")


@plugin.command()
@click.argument("kind", type=click.Choice(sorted(BY_NAME)))
@click.option("--name", required=True, help="Lowercase name, such as a jurisdiction code.")
@click.option("--built-in", is_flag=True, help="Write a folder inside the core instead.")
@click.option(
    "--root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path(),
    show_default=True,
    help="Where to write: the parent folder of the package, or the core's root.",
)
def new(kind: str, name: str, built_in: bool, root: Path) -> None:
    """Write a plugin skeleton with stubs, a conformance test and a samples folder."""
    plugin_kind = kind_named(kind)
    try:
        if built_in:
            folder = scaffold.new_built_in(plugin_kind, name, root)
        else:
            folder = scaffold.new_package(plugin_kind, name, root)
    except (ValueError, FileExistsError, FileNotFoundError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"wrote {folder}")
    if not built_in:
        click.echo(f"install it with: uv pip install -e {folder}")


@plugin.command(name="test")
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def test_command(path: Path) -> None:
    """Run the plugin's conformance suite on its own samples."""
    try:
        report = conformance.run(path)
    except (FileNotFoundError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(report.line())
    for problem in report.problems:
        click.echo(f"  - {problem}")
    if not report.passed:
        raise SystemExit(1)
