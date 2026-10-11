"""`casebench target check`: send one sample case and show what came back."""

import asyncio
from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, load_config
from casebench.runs.log import Result
from casebench.targets.sample import SAMPLE_QUESTION, send_sample


@click.group()
def target() -> None:
    """Connect and check the AI under test."""


def describe(result: Result) -> list[str]:
    lines = [
        f"answer     {result.output}",
        f"citations  {', '.join(result.citations) or 'none'}",
        f"documents  {', '.join(result.documents) or 'none'}",
        f"steps      {len(result.steps)} captured",
    ]
    for step in result.steps:
        ids = f" ({', '.join(step.doc_ids_out)})" if step.doc_ids_out else ""
        lines.append(f"  {step.kind.value} {step.name or step.model or ''}".rstrip() + ids)
    lines.append(f"took       {result.latency_ms:.0f} ms")
    return lines


@target.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option("--question", default=SAMPLE_QUESTION, show_default=True)
def check(config_path: Path, question: str) -> None:
    """Send one sample case and show the parsed answer, citations and captured steps."""
    try:
        result = asyncio.run(send_sample(load_config(config_path), question))
    except (FileNotFoundError, ValueError, LookupError) as error:
        raise click.ClickException(str(error)) from error
    if result.error:
        raise click.ClickException(f"the sample case failed: {result.error}")
    for line in describe(result):
        click.echo(line)
