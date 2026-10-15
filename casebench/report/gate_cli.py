"""`casebench gate`: fail a build when a run falls significantly below its baseline (0048)."""

from pathlib import Path

import click

from casebench.report.gate import CANNOT_JUDGE, CannotJudge, gate, lines, markdown

RUN = click.Path(exists=True, file_okay=False, path_type=Path)


@click.command(name="gate")
@click.argument("baseline", type=RUN)
@click.argument("run", type=RUN)
@click.option(
    "--include-unreviewed",
    is_flag=True,
    help="Gate cases no lawyer has approved yet too, such as court-derived ones.",
)
@click.option(
    "--markdown",
    "markdown_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the pull request comment here.",
)
def gate_command(
    baseline: Path, run: Path, include_unreviewed: bool, markdown_path: Path | None
) -> None:
    """Compare a run with a saved baseline of the same suite. Exits 1 when a metric falls
    significantly, 2 when the two runs were measured differently, 0 otherwise."""
    try:
        gated = gate(baseline, run, include_unreviewed)
    except CannotJudge as error:
        click.echo(f"gate: cannot judge: {error}", err=True)
        raise SystemExit(CANNOT_JUDGE) from error
    for line in lines(gated):
        click.echo(line)
    if markdown_path is not None:
        markdown_path.write_text(markdown(gated), encoding="utf-8")
    raise SystemExit(gated.code)
