"""`casebench extract`: read a sample of decisions with two models and keep agreed keys."""

from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, ConfigError, load_config
from casebench.corpus.binding import Corpus
from casebench.corpus.check import sample_ids
from casebench.corpus.interface import ListingNotSupported
from casebench.extract.agreement import FIELDS
from casebench.extract.run import extract, write
from casebench.judge.client import Judge

DEFAULT_KEYS = Path(".casebench") / "keys"


@click.command(name="extract")
@click.option(
    "--sample",
    "size",
    type=click.IntRange(min=1),
    required=True,
    help="How many decisions to read.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option(
    "--query",
    "queries",
    multiple=True,
    help="A search that finds decisions, for a store that cannot list them.",
)
@click.option(
    "--out",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_KEYS,
    show_default=True,
)
@click.option("--max-concurrency", type=click.IntRange(min=1), default=1, show_default=True)
def extract_command(
    size: int, config_path: Path, queries: tuple[str, ...], out: Path, max_concurrency: int
) -> None:
    """Two different models read each decision; only the fields they agree on become keys."""
    config = load_config(config_path)
    if config.corpus is None or config.extract is None:
        raise ConfigError(
            "extract needs `corpus:` and `extract: {models: [..two..]}` in the config"
        )
    corpus = Corpus(config.corpus)
    models = [Judge(model) for model in config.extract.models]
    try:
        ids = sample_ids(corpus, list(queries), size)
    except ListingNotSupported as error:
        raise click.ClickException(f"{error}; pass --query to sample through search") from error
    with click.progressbar(length=len(ids), label="reading decisions") as bar:
        result = extract(
            corpus,
            models,
            ids,
            workers=max_concurrency,
            progress=lambda done: bar.update(done - bar.pos),
        )
    write(result, models, out)
    click.echo(f"{result.decisions} decisions read, {len(result.keys)} answer keys kept")
    for name in FIELDS:
        click.echo(f"  {name:<11} agreement {result.rate(name):.2f}")
    for failure in result.failures:
        click.echo(f"  failed: {failure}")
    click.echo(str(out))
