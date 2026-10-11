"""`casebench target check`: send one sample case and show what came back."""

import asyncio
from pathlib import Path

import click

from casebench.adapters.citations import citation_parser
from casebench.config import DEFAULT_CONFIG, load_config
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.runner import ask
from casebench.targets.load import target_from_config

SAMPLE_QUESTION = "What is the time limit for appealing a first-instance civil judgment?"


@click.group()
def target() -> None:
    """Connect and check the AI under test."""


async def _check(config_path: Path, question: str) -> None:
    config = load_config(config_path)
    parse = None
    if config.corpus is not None:
        parse = citation_parser(config.corpus.jurisdiction, config.corpus.adapter_source)
    agent = target_from_config(config.target)
    sample = Case(
        id="target-check",
        task=Task.model_validate({"type": "qa", "question": question}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )
    await agent.start()
    try:
        result = await ask(sample, agent, parse)
    finally:
        await agent.stop()
    if result.error:
        raise click.ClickException(f"the sample case failed: {result.error}")
    click.echo(f"answer     {result.output}")
    click.echo(f"citations  {', '.join(result.citations) or 'none'}")
    click.echo(f"documents  {', '.join(result.documents) or 'none'}")
    click.echo(f"steps      {len(result.steps)} captured")
    for step in result.steps:
        click.echo(f"  {step.kind.value} {step.name or step.model or ''}".rstrip())
    click.echo(f"took       {result.latency_ms:.0f} ms")


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
        asyncio.run(_check(config_path, question))
    except (FileNotFoundError, ValueError, LookupError) as error:
        raise click.ClickException(str(error)) from error
