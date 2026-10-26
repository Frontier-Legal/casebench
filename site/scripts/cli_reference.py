"""Write the site's command-line reference page from the commands' own help.

Run from the repository root with `uv run python site/scripts/cli_reference.py`. A test fails
when the page in the repository differs from what this script writes, so the reference follows
every change to an option or a help text.
"""

import inspect
from pathlib import Path

import click

from casebench.cli import main

PAGE = Path(__file__).resolve().parents[1] / "src/content/docs/developers/reference/cli.md"

HEADER = """\
---
title: Command line
description: Every casebench command with its arguments and options, from the commands' own help.
sidebar:
  order: 1
---

Every command reads `casebench.yaml` in the current folder unless `--config` names another file.
`casebench COMMAND --help` prints the same text in a terminal.
"""


def _escaped(text: str) -> str:
    """Braces and angle brackets as literal text, so the page also parses as MDX."""
    for character in "{}<":
        text = text.replace(character, f"\\{character}")
    return text


def _cell(text: str) -> str:
    return _escaped(" ".join(text.split())).replace("|", "\\|")


def _paragraphs(text: str) -> str:
    """Help text as Markdown: lines wrapped for a terminal are joined, paragraphs kept."""
    blocks = inspect.cleandoc(click.unstyle(text)).split("\n\n")
    return "\n\n".join(_escaped(" ".join(block.split())) for block in blocks)


def _options(command: click.Command, context: click.Context) -> list[str]:
    rows: list[str] = []
    for param in command.get_params(context):
        if not isinstance(param, click.Option) or "--help" in param.opts:
            continue
        record = param.get_help_record(context)
        if record is None:
            continue
        flags, help_text = record
        rows.append(f"| `{_cell(flags)}` | {_cell(help_text)} |")
    if not rows:
        return []
    return ["| Option | Description |", "| --- | --- |", *rows, ""]


def _section(command: click.Command, path: list[str], parent: click.Context | None) -> list[str]:
    name = " ".join(path)
    context = click.Context(command, info_name=path[-1], parent=parent)
    lines: list[str] = []
    if parent is not None:
        lines += [f"{'#' * min(len(path), 4)} `{name}`", ""]
    usage = " ".join([context.command_path, *command.collect_usage_pieces(context)])
    lines += ["```sh", usage, "```", ""]
    if command.help:
        lines += [_paragraphs(command.help), ""]
    lines += _options(command, context)
    if isinstance(command, click.Group):
        for child in command.list_commands(context):
            sub = command.get_command(context, child)
            if sub is not None and not sub.hidden:
                lines += _section(sub, [*path, child], context)
    return lines


def render() -> str:
    body = _section(main, ["casebench"], None)
    return HEADER + "\n" + "\n".join(body).rstrip() + "\n"


if __name__ == "__main__":
    PAGE.write_text(render(), encoding="utf-8")
    print(f"wrote {PAGE}")
