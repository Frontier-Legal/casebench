"""`casebench review`: a lawyer's verdict on the judge's, kept in the run's folder (0047)."""

from pathlib import Path
from typing import cast

import click

from casebench.report.calibration import (
    CannotRecord,
    Said,
    calibration,
    read_reviews,
    record_verdict,
)
from casebench.report.render import calibration_lines
from casebench.runs.log import RunLog

RUN = click.Path(exists=True, file_okay=False, path_type=Path)


@click.group(name="review")
def review_group() -> None:
    """Record a lawyer's verdict beside the judge's."""


@review_group.command(name="criterion")
@click.argument("run_dir", type=RUN)
@click.option("--case", "case_id", required=True, help="The case's id.")
@click.option("--criterion", "criterion_id", required=True, help="The criterion's id.")
@click.option("--repeat", type=click.IntRange(min=0), default=0, show_default=True)
@click.option(
    "--verdict",
    type=click.Choice(["pass", "fail"]),
    required=True,
    help="Whether the answer passes this criterion, in the lawyer's view.",
)
@click.option("--by", "by", required=True, help="Who gives the verdict.")
@click.option("--note", help="Why; required when the verdict overrules the judge's.")
def criterion_command(
    run_dir: Path,
    case_id: str,
    criterion_id: str,
    repeat: int,
    verdict: str,
    by: str,
    note: str | None,
) -> None:
    """Give a lawyer's verdict on one criterion of a scored run. It is counted against the
    judge's in the run's report; the scores stay the judge's."""
    try:
        said = cast(Said, verdict)
        review = record_verdict(run_dir, case_id, repeat, criterion_id, said, by, note)
    except CannotRecord as failure:
        raise click.ClickException(str(failure).replace("a note", "--note")) from None
    judge = review.judge
    agreed = "agrees with" if verdict == judge else "overrules"
    click.echo(f"recorded: {by} says {verdict}, which {agreed} the judge ({judge})")
    click.echo(
        "it replaces the judge's verdict in the scores the next time the run is scored; "
        "scoring again reads the judge's kept replies and asks the judge nothing"
    )
    scores = RunLog.read_scores(RunLog(run_dir).score_sets()[-1])
    for line in calibration_lines(calibration(scores, read_reviews(run_dir))):
        click.echo(line)
