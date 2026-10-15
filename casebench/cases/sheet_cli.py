"""`casebench template lawyer` and `casebench import`: cases from a spreadsheet (decision 0049)."""

from pathlib import Path

import click

from casebench.cases.cli import CONFIG, _config, _listed, _resolver
from casebench.cases.resolve import resolve_case, unresolved
from casebench.cases.rows import row_case
from casebench.cases.sheet import SheetError, read_rows, task_names, write_template
from casebench.cases.suite import existing, save
from casebench.core.case import Case
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.report.review_sheet import run_of
from casebench.report.review_sheet_cli import import_review_sheet


def _unevidenced(case: Case) -> list[str]:
    """The metrics a case names that have nothing to earn in it (decision 0047)."""
    out = []
    for name in case.metrics:
        check = getattr(registry.load(kind_named("metric"), name), "evidenced", None)
        if check is not None and not check(case):
            out.append(name)
    return out


@click.group(name="template")
def template_group() -> None:
    """Write a file for someone to fill in."""


@template_group.command(name="lawyer")
@click.option("--task", type=click.Choice(task_names()), default="qa", show_default=True)
@click.option("--out", "path", type=click.Path(dir_okay=False, path_type=Path))
def lawyer_template(task: str, path: Path | None) -> None:
    """A spreadsheet a lawyer fills with one case per row: XLSX, or CSV when --out ends in .csv."""
    path = path or Path(f"cases-{task}.xlsx")
    if path.exists():
        raise click.ClickException(f"{path} exists; name another file with --out")
    write_template(path, task)
    click.echo(f"wrote {path}: one case per row, under the columns of {task}")
    click.echo(f"then: casebench import {path} --suite DIR --by NAME")


@click.command(name="import")
@click.argument("path", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--suite",
    "suite_dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="The suite folder cases join; it is created when it does not exist.",
)
@click.option(
    "--by",
    "author",
    help="The lawyer who wrote the cases, or who reviewed the rows naming no reviewer.",
)
@click.option("--task", type=click.Choice(task_names()), help="The task of a CSV's rows.")
@click.option(
    "--runs-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Where the run a review sheet reviews is; .casebench/runs by default.",
)
@click.option("--database", help="The workbench's database, whose event log keeps verdicts.")
@CONFIG
def import_command(
    path: Path,
    suite_dir: Path | None,
    author: str | None,
    task: str | None,
    runs_dir: Path | None,
    database: str | None,
    config_path: Path,
) -> None:
    """Add a spreadsheet's rows to a suite as cases approved by the lawyer who wrote them, or
    read a review sheet's verdicts back into its run (decisions 0049, 0055)."""
    reviewed = run_of(path)
    if reviewed is not None:
        import_review_sheet(path, reviewed, runs_dir, author, database)
        return
    if suite_dir is None or not author:
        raise click.ClickException("a sheet of cases needs --suite and --by")
    try:
        rows = read_rows(path, task)
        made = [(row, row_case(row, path, author)) for row in rows]
    except SheetError as failure:
        raise click.ClickException(str(failure)) from None
    if not made:
        raise click.ClickException(f"{path.name} has no filled row")
    _, cases = existing(suite_dir)
    taken = {case.id for case in cases}
    for row, case in made:
        if case.id in taken:
            raise click.ClickException(
                f"{row.where(path)}: {suite_dir} already has a case {case.id}"
            )
        taken.add(case.id)
    resolver = _resolver(_config(config_path))
    if resolver is not None:
        made = [(row, resolve_case(case, resolver)) for row, case in made]
    old, manifest = save(suite_dir, [*cases, *(case for _, case in made)])
    click.echo(f"added {len(made)} cases from {path.name}, approved by {author}")
    for row, case in made:
        missing = _unevidenced(case)
        if missing:
            click.echo(
                f"  {case.id} (row {row.number}) is unevidenced for {', '.join(missing)}: the row "
                "gives nothing to grade against, so runs will not score it for them"
            )
        waiting = unresolved(case)
        if waiting:
            later = (
                "casebench case resolve" if resolver else "a corpus, then casebench case resolve"
            )
            click.echo(
                f"  {case.id}: not in the corpus yet: {_listed(waiting)}; they resolve with {later}"
            )
    click.echo(f"suite {manifest.suite_id}: {old or 'new'} -> {manifest.content_hash}")
