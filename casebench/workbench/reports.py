"""The runs the workbench reports on, and each run's error rates with its failing answers.

Lawyers' verdicts count in place of the judge's, as in the report (decisions 0047, 0054).
"""

from pydantic import BaseModel, Field

from casebench.report.calibration import lawyers_win, read_reviews
from casebench.report.errors import error_rates
from casebench.workbench.items import NotFound, answer_key, latest_scores, title_of
from casebench.workbench.sources import Workspace


class RunRow(BaseModel):
    run_id: str
    suite_id: str
    target: str
    scored: bool = Field(description="Whether the run has scores to report.")


class FailingAnswer(BaseModel):
    key: str = Field(description="The answer's item, which opens beside its evidence.")
    case_id: str
    repeat: int
    title: str


class RateView(BaseModel):
    error: str
    meaning: str
    n: int
    rate: float
    low: float
    high: float
    failing: list[FailingAnswer]


class RunReport(BaseModel):
    run_id: str
    suite_id: str
    target: str
    rates: list[RateView]


def runs(workspace: Workspace) -> list[RunRow]:
    """The newest first."""
    return [
        RunRow(
            run_id=log.info.run_id,
            suite_id=log.info.suite_id,
            target=log.info.target,
            scored=bool(log.score_sets()),
        )
        for log in reversed(workspace.runs())
    ]


def run_report(workspace: Workspace, run_id: str) -> RunReport:
    log = workspace.run(run_id)
    if log is None:
        raise NotFound(f"no run {run_id}")
    info = log.info
    suite = workspace.suites().get(info.suite_id)
    scores = lawyers_win(latest_scores(log), read_reviews(log.folder))
    rates = [
        RateView(
            **rate.model_dump(exclude={"failing"}),
            failing=[
                FailingAnswer(
                    key=answer_key(info.run_id, answer.case_id, answer.repeat),
                    case_id=answer.case_id,
                    repeat=answer.repeat,
                    title=title_of(suite.case(answer.case_id) if suite else None, answer.case_id),
                )
                for answer in rate.failing
            ],
        )
        for rate in error_rates(scores, info.suite_id)
    ]
    return RunReport(run_id=info.run_id, suite_id=info.suite_id, target=info.target, rates=rates)
