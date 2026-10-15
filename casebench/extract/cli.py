"""`casebench extract`: read a sample of decisions with two models and keep agreed keys."""

import sys
from pathlib import Path
from typing import Any

import click
import yaml

from casebench.config import DEFAULT_CONFIG, ConfigError, load_config
from casebench.corpus.check import sample_ids
from casebench.corpus.corpora import Corpora, NoSuchCorpus
from casebench.corpus.interface import ListingNotSupported
from casebench.extract.agreement import FIELDS
from casebench.extract.estimate import estimate
from casebench.extract.run import Progress, extract, write
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.perimeter import enforce
from casebench.providers.settings import SETTINGS

DEFAULT_KEYS = Path(".casebench") / "keys"


def _settings(given: tuple[str, ...]) -> dict[str, Any]:
    """`NAME=VALUE` pairs, each value read as YAML so numbers stay numbers."""
    settings = {}
    for pair in given:
        name, sep, value = pair.partition("=")
        if not sep or name not in SETTINGS:
            raise click.BadParameter(
                f"{pair!r} must be NAME=VALUE with NAME one of {', '.join(SETTINGS)}",
                param_hint="--set",
            )
        settings[name] = yaml.safe_load(value)
    return settings


def _cost(models: list[Judge]) -> str:
    costs = [m.cost for m in models]
    if None in costs:
        used = sum(m.input_tokens + m.output_tokens for m in models)
        return f"{used} tokens so far, cost unknown without a price"
    return f"${sum(c for c in costs if c is not None):.2f} so far"


def _line(models: list[Judge]) -> Any:
    """One line per decision, for a log file where a progress bar would show nothing (0038)."""

    def show(done: Progress) -> None:
        what = "failed" if done.failed else "read"
        click.echo(
            f"{what} {done.done}/{done.total} {done.decision_id} in {done.seconds:.1f}s, "
            f"{_cost(models)}"
        )

    return show


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
@click.option("--corpus", "corpus_name", help="Which corpus, when the config names several.")
@click.option(
    "--set",
    "given",
    multiple=True,
    metavar="NAME=VALUE",
    help="A model setting for both models in this run, such as reasoning_effort=low.",
)
@click.option("--dry-run", is_flag=True, help="Say what it would cost; send nothing.")
def extract_command(
    size: int,
    config_path: Path,
    queries: tuple[str, ...],
    out: Path,
    max_concurrency: int,
    corpus_name: str | None,
    given: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Two different models read each decision; only the fields they agree on become keys."""
    config = load_config(config_path)
    enforce(config)
    if not config.corpora or config.extract is None:
        raise ConfigError(
            "extract needs `corpus:` and `extract: {models: [..two..]}` in the config"
        )
    try:
        corpus = Corpora(config.corpora).only(corpus_name)
    except NoSuchCorpus as error:
        raise click.ClickException(str(error)) from error
    settings = _settings(given)
    configs: list[JudgeConfig] = [
        model.model_copy(update={"options": {**model.options, **settings}})
        for model in config.extract.models
    ]
    if dry_run:
        for line in estimate(corpus.connector.folder, configs, size).lines():
            click.echo(line)
        return
    models = [Judge(model) for model in configs]
    try:
        ids = sample_ids(corpus, list(queries), size)
    except ListingNotSupported as error:
        raise click.ClickException(f"{error}; pass --query to sample through search") from error
    if sys.stdout.isatty():
        with click.progressbar(length=len(ids), label="reading decisions") as bar:
            result = extract(
                corpus,
                models,
                ids,
                workers=max_concurrency,
                progress=lambda done: bar.update(done.done - bar.pos),
            )
    else:
        result = extract(corpus, models, ids, workers=max_concurrency, progress=_line(models))
    write(result, models, out, corpus.name)
    click.echo(
        f"{result.decisions} decisions read, {len(result.keys)} answer keys kept, in "
        f"{result.seconds:.0f}s, {_cost(models).removesuffix(' so far')}"
    )
    for name in FIELDS:
        click.echo(f"  {name:<11} agreement {result.rate(name):.2f}")
    for failure in result.failures:
        click.echo(f"  failed: {failure}")
    click.echo(str(out))
