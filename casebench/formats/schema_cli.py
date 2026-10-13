"""`casebench schema export`: write each format's JSON Schema at its current version."""

from pathlib import Path

import click

from casebench.formats.files import SCHEMAS, is_released, schema_path
from casebench.formats.registry import FORMATS
from casebench.formats.schema import schema_text


@click.group(name="schema")
def schema() -> None:
    """The JSON Schemas of Casebench's formats."""


@schema.command(name="export")
@click.option(
    "--into",
    type=click.Path(file_okay=False, path_type=Path),
    default=SCHEMAS,
    show_default="the schemas shipped with Casebench",
    help="The folder to write into; one subfolder per format.",
)
def export_command(into: Path) -> None:
    """Write every format's schema at its current version, one file per version."""
    for item in FORMATS.values():
        path = schema_path(item.version, into)
        text = schema_text(item.model)
        unchanged = path.is_file() and path.read_text(encoding="utf-8") == text
        if into.resolve() == SCHEMAS.resolve() and is_released(item.version) and not unchanged:
            raise click.ClickException(
                f"{item.version} is released and its schema never changes; "
                f"raise the version of the {item.version.name} format first"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        click.echo(f"{'unchanged' if unchanged else 'wrote':<9} {path}")
