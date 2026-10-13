"""`casebench validate`: check a file against its format's schema and the rules it cannot hold."""

import json
import warnings
from pathlib import Path
from typing import Any

import click
import yaml
from pydantic import ValidationError

from casebench.formats.read import ignored_note, read
from casebench.formats.registry import named
from casebench.formats.version import FormatVersion, UnreadableFormat
from casebench.suites.freeze import MANIFEST_FILE, SUITE_FILE, SuiteHashMismatch, load


def _records(path: Path) -> list[tuple[str, Any]]:
    """Each record with where it is: the lines of a `.jsonl` file, or one JSON or YAML
    document (a profile is YAML)."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [
            (f"line {number}", json.loads(line))
            for number, line in enumerate(text.splitlines(), start=1)
            if line.strip()
        ]
    if path.suffix in (".yaml", ".yml"):
        return [(path.name, yaml.safe_load(text))]
    return [(path.name, json.loads(text))]


def _declared(path: Path, records: list[tuple[str, Any]], given: str | None) -> FormatVersion:
    """The `--format` given; else the file's own `format` field; else, for a suite's lines,
    the case format its manifest names."""
    if given:
        return FormatVersion.parse(given)
    first = records[0][1] if records else {}
    if isinstance(first, dict) and "format" in first and len(records) == 1:
        return FormatVersion.parse(first["format"])
    manifest = path.parent / MANIFEST_FILE
    if path.suffix == ".jsonl" and manifest.is_file():
        return FormatVersion.parse(json.loads(manifest.read_text("utf-8")).get("case_format"))
    raise UnreadableFormat(f"{path} names no format; pass --format, such as casebench.document/1.0")


def _suite_problems(path: Path) -> list[str]:
    """A suite's manifest or lines, checked together: the cases must hash to the manifest's
    hash, which no schema of either file can say."""
    folder = path.parent
    if path.name not in (MANIFEST_FILE, SUITE_FILE) or not (folder / SUITE_FILE).is_file():
        return []
    if not (folder / MANIFEST_FILE).is_file():
        return []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            load(folder)
    except SuiteHashMismatch as error:
        return [f"{folder}: {error}"]
    return []


def _problems(where: str, error: ValidationError) -> list[str]:
    return [
        f"{where}: {'.'.join(str(p) for p in item['loc']) or '(the record)'}: {item['msg']}"
        for item in error.errors()
    ]


@click.command(name="validate")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--format", "given", help="The file's format, such as casebench.document/1.0.")
def validate_command(path: Path, given: str | None) -> None:
    """Check a file against its format: the schema, and the rules a schema cannot hold."""
    records = _records(path)
    declared = _declared(path, records, given)
    item = named(declared.name)
    problems: list[str] = []
    ignored: list[str] = []
    for where, data in records:
        try:
            _, skipped = read(item.model, data, declared, item.version)
        except ValidationError as error:
            problems += _problems(where, error)
            continue
        ignored += skipped
    if not problems:
        problems = _suite_problems(path)
    for line in problems:
        click.echo(line, err=True)
    if ignored:
        click.echo(ignored_note(str(path), declared, item.version, ignored), err=True)
    if problems:
        raise click.ClickException(f"{path} is not valid {declared}")
    click.echo(f"{path}: valid {declared}, {len(records)} record(s)")
