"""`casebench corpus`: add a store, check it on a sample, clear its cache."""

from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, load_config
from casebench.corpus import cache
from casebench.corpus.add_cli import add
from casebench.corpus.check import SAMPLE_SIZE, check
from casebench.corpus.corpora import Corpora, NoSuchCorpus
from casebench.corpus.interface import ListingNotSupported


@click.group()
def corpus() -> None:
    """The documents citations are checked against."""


corpus.add_command(add)


@corpus.command(name="check")
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
    help="A search that finds documents, for a store that cannot list them.",
)
@click.option("--size", type=click.IntRange(min=1), default=SAMPLE_SIZE, show_default=True)
@click.option("--corpus", "corpus_name", help="Which corpus, when the config names several.")
def check_command(
    config_path: Path, queries: tuple[str, ...], size: int, corpus_name: str | None
) -> None:
    """Fetch a sample by id and report which required fields are present or missing."""
    config = load_config(config_path)
    if not config.corpora:
        raise click.ClickException("the config has no corpus; add one with casebench corpus add")
    try:
        store = Corpora(config.corpora).only(corpus_name)
    except NoSuchCorpus as error:
        raise click.ClickException(str(error)) from error
    try:
        report = check(store, list(queries), size)
    except ListingNotSupported as error:
        raise click.ClickException(f"{error}; pass --query to sample through search") from error
    click.echo(
        f"sampled {report.sampled} documents ({report.fetched} fetched, "
        f"{report.sampled - report.fetched} from the cache)"
    )
    for name, count in report.present.items():
        click.echo(f"  {name:<13} {count}/{report.sampled} present")
    for failure in report.failures:
        click.echo(f"  failed: {failure}")
    if report.missing:
        click.echo(f"missing in some documents: {', '.join(report.missing)}")


@corpus.group(name="cache")
def cache_group() -> None:
    """The local copy of fetched documents."""


@cache_group.command(name="clear")
def clear() -> None:
    """Delete every cached document."""
    click.echo(f"removed {cache.clear()} cached documents")
