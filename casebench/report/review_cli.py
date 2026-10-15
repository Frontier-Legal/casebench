"""`casebench review`: a lawyer's verdict on the judge's, kept in the run's folder (0047)."""

from pathlib import Path

import click

from casebench.report.calibration import (
    LawyerVerdict,
    add_review,
    calibration,
    criterion_verdicts,
    read_reviews,
    said,
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
    sets = RunLog(run_dir).score_sets()
    if not sets:
        raise click.ClickException(f"{run_dir} has no scores yet; score it first")
    scores = RunLog.read_scores(sets[-1])
    judged = criterion_verdicts(scores).get((case_id, repeat, criterion_id))
    if judged is None:
        raise click.ClickException(
            f"the latest score set has no criteria verdict for case {case_id}, repeat {repeat}, "
            f"criterion {criterion_id}"
        )
    judge = said(judged)
    if verdict != judge and not note:
        raise click.ClickException(f"the judge said {judge}; overruling it needs --note saying why")
    add_review(
        run_dir,
        LawyerVerdict(
            case_id=case_id,
            repeat=repeat,
            criterion_id=criterion_id,
            verdict=verdict,  # type: ignore[arg-type]
            judge=judge,
            note=note,
            by=by,
        ),
    )
    agreed = "agrees with" if verdict == judge else "overrules"
    click.echo(f"recorded: {by} says {verdict}, which {agreed} the judge ({judge})")
    click.echo(
        "it replaces the judge's verdict in the scores the next time the run is scored; "
        "scoring again reads the judge's kept replies and asks the judge nothing"
    )
    for line in calibration_lines(calibration(scores, read_reviews(run_dir))):
        click.echo(line)
