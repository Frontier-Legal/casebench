"""`casebench generate`: freeze a court-derived suite from extracted answer keys."""

from datetime import date, datetime
from pathlib import Path

import click

from casebench.extract.cli import DEFAULT_KEYS
from casebench.extract.run import read_keys
from casebench.suites.court import FACT_KINDS, NotEnoughLevels, court_suite
from casebench.suites.freeze import freeze


@click.command(name="generate")
@click.option(
    "--keys",
    "keys_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=DEFAULT_KEYS,
    show_default=True,
)
@click.option(
    "--types",
    default="outcome,statute,precedent",
    show_default=True,
    help="Comma-separated case types.",
)
@click.option("--n", "count", type=click.IntRange(min=1), required=True)
@click.option(
    "--after",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Only decisions dated after this day, such as a model's training cutoff.",
)
@click.option("--stratify", type=click.Choice(["court"]), help="Balance across court levels.")
@click.option("--suite-id", required=True, help="The suite's name; it also seeds its order.")
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), required=True)
def generate_command(
    keys_dir: Path,
    types: str,
    count: int,
    after: datetime | None,
    stratify: str | None,
    suite_id: str,
    out: Path,
) -> None:
    """Turn answer keys into cases and freeze them as a suite."""
    wanted = [t.strip() for t in types.split(",") if t.strip()]
    unknown = sorted(set(wanted) - set(FACT_KINDS))
    if unknown:
        raise click.BadParameter(f"unknown types {unknown}; choose from {sorted(FACT_KINDS)}")
    cutoff: date | None = after.date() if after else None
    try:
        cases, generation = court_suite(
            suite_id, read_keys(keys_dir), wanted, count, after=cutoff, stratify=stratify == "court"
        )
    except NotEnoughLevels as error:
        raise click.ClickException(str(error)) from error
    manifest = freeze(suite_id, cases, out, generation)
    if cutoff:
        click.echo(
            f"cutoff {cutoff}: {generation['decisions_allowed']} decisions allowed, "
            f"{generation['decisions_excluded_by_date']} excluded"
        )
    click.echo(f"suite {manifest.suite_id}: {manifest.case_count} cases {manifest.task_types}")
    click.echo(f"{manifest.content_hash}\n{out}")
