"""The report a partner reads: one run's figures by task and practice area, over approved cases.

It holds the four error rates, worked examples beside their evidence, and who approved the
golden data (decision 0054). The HTML, PDF and DOCX writers lay it out.
"""

from collections import Counter, defaultdict
from datetime import UTC, datetime

from casebench import __version__
from casebench.core.case import Approval, Case
from casebench.core.model import FrozenRecord
from casebench.core.score import CitationLabel, Score
from casebench.report.calibration import lawyers_win, read_reviews
from casebench.report.errors import ErrorRate, error_rates
from casebench.report.statistics import mean, mean_interval
from casebench.runs.log import Result, RunLog

# What a partner reads for each built-in metric; another metric is shown by its name.
METRIC_NAMES = {
    "criteria": "Criteria met, weighted",
    "citation_integrity": "Citations verified",
    "outcome": "Ruling correct",
    "statute": "Statutes the court applied (F1)",
    "precedent": "Precedents the court relied on (F1)",
    "authority_recall": "Key authorities found",
    "authority_ndcg": "Key authorities ranked first",
    "fields": "Fields extracted correctly",
    "issues_found": "Issues found",
    "edit_preservation": "Text left as it was outside the edit",
}
EXAMPLES_PER_ERROR = 3
# An answer longer than this is cut in the report; the run keeps it whole.
ANSWER_CHARS = 1500
NO_AREA = "No practice area"


class MetricRow(FrozenRecord):
    task_type: str
    metric: str
    name: str
    practice_area: str | None
    n: int
    mean: float
    low: float
    high: float


class Shown(FrozenRecord):
    """One piece of evidence beside a worked example, such as the court's passage."""

    label: str
    text: str


class Example(FrozenRecord):
    error: str
    case_id: str
    practice_area: str | None
    question: str
    answer: str
    evidence: list[Shown]


class Approver(FrozenRecord):
    name: str
    cases: int


class PartnerReport(FrozenRecord):
    suite_id: str
    suite_hash: str
    run_id: str
    target: str
    scored_on: str
    exported_on: str
    casebench_version: str
    cases: int
    approved: int
    unreviewed: int
    not_recorded: int = 0
    approvers: list[Approver]
    left_out: int = 0
    metrics: list[MetricRow]
    error_rates: list[ErrorRate]
    examples: list[Example]


def area_name(area: str | None) -> str:
    return area or NO_AREA


def question_of(case: Case | None) -> str:
    if case is None:
        return ""
    inputs = case.task.inputs
    return str(inputs.get("question") or inputs.get("instruction") or "")


def _metrics(scores: list[Score], suite_id: str) -> list[MetricRow]:
    grouped: dict[tuple[str, str, str | None], list[float]] = defaultdict(list)
    for score in scores:
        grouped[(score.task_type, score.metric, score.practice_area)].append(score.value)
    rows = []
    for (task, metric, area), values in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2] is None, item[0][2])
    ):
        interval = mean_interval(values, suite_id)
        rows.append(
            MetricRow(
                task_type=task,
                metric=metric,
                name=METRIC_NAMES.get(metric, metric),
                practice_area=area,
                n=len(values),
                mean=mean(values),
                low=interval.low,
                high=interval.high,
            )
        )
    return rows


def _cut(text: str) -> str:
    return text if len(text) <= ANSWER_CHARS else text[:ANSWER_CHARS].rstrip() + " […]"


def _facts(case: Case | None, kind: str, label: str) -> list[Shown]:
    """The court's passage for each fact of a kind, else what the lawyer wrote."""
    if case is None:
        return []
    return [
        Shown(
            label=label,
            text=f"{fact.value}: “{fact.evidence.quote}”" if fact.evidence.quote else fact.value,
        )
        for fact in case.reference.facts
        if fact.kind == kind
    ]


def _evidence(error: str, scores: list[Score], case: Case | None) -> list[Shown]:
    if error in ("fabricated citation", "unsupported claim"):
        wanted = (
            CitationLabel.FABRICATED
            if error == "fabricated citation"
            else CitationLabel.MISGROUNDED
        )
        return [
            Shown(
                label=f"Cited for “{check.claim}”" if check.claim else "Cited",
                text=f"{check.citation}. The corpus: "
                + (
                    check.reason
                    or (f"“{check.quote}”" if check.quote else "no such decision or statute")
                ),
            )
            for score in scores
            for check in score.citations
            if check.label is wanted
        ]
    if error == "wrong outcome":
        shown = _facts(case, "outcome", "The ruling")
        return shown or _facts(case, "answer", "The lawyer's answer")
    if error == "wrong statute":
        found = [s.explanation for s in scores if s.metric == "statute" and s.explanation]
        return _facts(case, "statute", "The court applied") + [
            Shown(label="Measured", text=text) for text in found
        ]
    return []


def _examples(
    rates: list[ErrorRate],
    scores: list[Score],
    results: dict[tuple[str, int], Result],
    cases: dict[str, Case],
) -> list[Example]:
    by_answer: dict[tuple[str, int], list[Score]] = defaultdict(list)
    for score in scores:
        by_answer[(score.case_id, score.repeat)].append(score)
    out = []
    for rate in rates:
        for answer in rate.failing[:EXAMPLES_PER_ERROR]:
            key = (answer.case_id, answer.repeat)
            case = cases.get(answer.case_id)
            result = results.get(key)
            said = (result.output or result.error or "") if result else ""
            out.append(
                Example(
                    error=rate.error,
                    case_id=answer.case_id,
                    practice_area=case.practice_area if case else None,
                    question=question_of(case),
                    answer=_cut(said),
                    evidence=_evidence(rate.error, by_answer[key], case),
                )
            )
    return out


def _approvers(cases: list[Case]) -> tuple[list[Approver], int]:
    """Each approver with the cases they approved, and the approved cases naming none."""
    named = Counter(case.approver for case in cases if case.approval is Approval.APPROVED)
    missing = named.pop(None, 0)
    approvers = [Approver(name=name, cases=n) for name, n in named.most_common() if name]
    return approvers, missing


def partner_report(log: RunLog, cases: list[Case]) -> PartnerReport:
    """`cases` are the suite's, as frozen with the hash the run ran. Lawyers' verdicts count
    in place of the judge's, and only lawyer-approved cases are counted, as in the gate."""
    info = log.info
    sets = log.score_sets()
    if not sets:
        raise ValueError(f"{log.folder} has no scores yet; score it first")
    by_id = {case.id: case for case in cases}
    # The suite names each case's practice area, also for scores made before scores did.
    scores = [
        s.model_copy(update={"practice_area": by_id[s.case_id].practice_area})
        if s.case_id in by_id
        else s
        for s in lawyers_win(RunLog.read_scores(sets[-1]), read_reviews(log.folder))
    ]
    approved = [s for s in scores if s.approval is Approval.APPROVED]
    left_out = len(
        {(s.case_id, s.repeat) for s in scores} - {(s.case_id, s.repeat) for s in approved}
    )
    rates = error_rates(approved, info.suite_id)
    results = {(r.case_id, r.repeat): r for r in log.results()}
    approvers, missing = _approvers(cases)
    scored_on = datetime.fromtimestamp(sets[-1].stat().st_mtime, UTC).date().isoformat()
    return PartnerReport(
        suite_id=info.suite_id,
        suite_hash=info.suite_hash,
        run_id=info.run_id,
        target=info.target,
        scored_on=scored_on,
        exported_on=datetime.now(UTC).date().isoformat(),
        casebench_version=__version__,
        cases=len(cases),
        approved=sum(1 for c in cases if c.approval is Approval.APPROVED),
        unreviewed=sum(1 for c in cases if c.approval is Approval.DRAFT),
        not_recorded=missing,
        approvers=approvers,
        left_out=left_out,
        metrics=_metrics(approved, info.suite_id),
        error_rates=rates,
        examples=_examples(rates, approved, results, by_id),
    )


# How to read the report, the same in every format.
READING = [
    "Every figure counts only the cases a lawyer approved; unreviewed cases are left out and "
    "counted.",
    "Each figure comes with its 95% interval: with this many cases, the true figure most likely "
    "lies within it. Two figures whose intervals overlap may not differ at all.",
    "No figure mixes tasks or practice areas.",
]


def percent(value: float) -> str:
    return f"{value:.0%}"


def interval(low: float, high: float) -> str:
    return f"{low:.0%} to {high:.0%}"


def approval_lines(report: PartnerReport) -> list[str]:
    """Who approved the answer key the run was scored against, in sentences."""
    lines = [
        f"{report.approved} of the suite's {report.cases} cases are approved by a lawyer"
        + (f"; {report.unreviewed} are unreviewed and not counted." if report.unreviewed else ".")
    ]
    lines += [
        f"{a.name} approved {a.cases} case{'' if a.cases == 1 else 's'}." for a in report.approvers
    ]
    if report.not_recorded:
        lines.append(f"For {report.not_recorded} approved cases the approver is not recorded.")
    return lines
