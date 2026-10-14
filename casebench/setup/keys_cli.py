"""`casebench keys`: where a variable is kept, by name, and never its value."""

import json
import os
from pathlib import Path
from typing import Any

import click

from casebench import envfiles, keys


def _where(name: str, root: Path) -> dict[str, Any]:
    """The shell, and each of the project's .env files that gives the name a value, with a
    fingerprint so files that disagree can be told apart (decisions 0043 and 0044)."""
    holding = envfiles.holders(name, root)
    return {
        "name": name,
        "in_shell": bool(os.environ.get(name)),
        "files": [
            {"file": path.relative_to(root).as_posix(), "fingerprint": keys.fingerprint(value)}
            for path, value in holding.items()
        ],
        "values_agree": len(set(holding.values())) <= 1,
    }


def _said(found: dict[str, Any]) -> list[str]:
    lines = [f"{found['name']}: {'set' if found['in_shell'] else 'not set'} in this shell"]
    lines += [f"  {item['file']}  (fingerprint {item['fingerprint']})" for item in found["files"]]
    if not found["files"]:
        lines.append("  in no .env file here")
    elif not found["values_agree"]:
        lines.append(f"  the values differ; pass --key {found['name']}=FILE to say which is used")
    return lines


@click.command(name="keys")
@click.argument("names", nargs=-1, required=True)
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="The project's folder, whose .env files are read.",
)
@click.option("--json", "as_json", is_flag=True, help="The same as JSON.")
def keys_command(names: tuple[str, ...], root: Path, as_json: bool) -> None:
    """Where each named variable is kept: the shell, and the project's .env files that give it
    a value. No value is printed; files that disagree show different fingerprints."""
    root = root.resolve()
    found = [_where(name, root) for name in names]
    if as_json:
        click.echo(json.dumps(found, indent=2))
        return
    for item in found:
        for line in _said(item):
            click.echo(line)
