"""`casebench corpus`: add a store, check it on a sample, clear its cache."""

from pathlib import Path

import click

from casebench.config import DEFAULT_CONFIG, load_config
from casebench.corpus import cache
from casebench.corpus.add_cli import add
from casebench.corpus.check import SAMPLE_SIZE, CheckReport, check
from casebench.corpus.corpora import Corpora, NoSuchCorpus
from casebench.corpus.interface import ListingNotSupported
from casebench.corpus.probe_cli import probe
from casebench.perimeter import enforce


@click.group()
def corpus() -> None:
    """The documents citations are checked against."""


corpus.add_command(add)
corpus.add_command(probe)


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
    enforce(config)
    if not config.corpora:
        raise click.ClickException("the config has no corpus; add one with casebench corpus add")
    try:
        store = Corpora(config.corpora).only(corpus_name)
    except NoSuchCorpus as error:
        raise click.ClickException(str(error)) from error
    paid = store.connector.keep_searches
    if paid and queries:
        kept = sum(store.connector.search_cached(query, size) for query in queries)
        click.echo(
            f"{store.name} charges per search: this check may make {len(queries)} searches, "
            f"{kept} of them already kept"
        )
    try:
        report = check(store, list(queries), size)
    except ListingNotSupported as error:
        raise click.ClickException(f"{error}; pass --query to sample through search") from error
    if paid and queries:
        click.echo(f"searched {store.connector.searched} times; the rest came from the cache")
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
    for line in _description_lines(report, bool(queries)):
        click.echo(line)


def _description_lines(report: CheckReport, searched: bool) -> list[str]:
    """What the judge sees of each search result to match a citation (decision 0037)."""
    if not searched:
        return ["pass --query to see what search results say about their documents"]
    lines = ["search results, as the judge sees them to match a citation:"]
    lines += [
        f"  {name:<13} {count}/{report.results} results" for name, count in report.described.items()
    ]
    if report.undescribed:
        lines.append(
            f"missing in some results: {', '.join(report.undescribed)}; Casebench describes "
            "those results from each document instead, which costs a fetch; map them with "
            "search_results and result_fields"
        )
    return lines


@corpus.group(name="cache")
def cache_group() -> None:
    """The local copy of fetched documents."""


@cache_group.command(name="clear")
def clear() -> None:
    """Delete every cached document."""
    documents, searches = cache.clear()
    click.echo(f"removed {documents} cached documents and {searches} cached searches")
