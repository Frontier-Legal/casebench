"""Report tables: one per task and metric, split by reference source and approval."""

from collections import defaultdict

from casebench.core.case import Approval, Case, ReferenceSource
from casebench.core.model import FrozenRecord
from casebench.core.score import Score
from casebench.report.baselines import majority_class, text_only
from casebench.report.statistics import mean, mean_interval

APPROVAL_LABELS = {Approval.APPROVED: "lawyer-approved", Approval.DRAFT: "unreviewed"}


class Row(FrozenRecord):
    reference_source: ReferenceSource
    approval: str
    n: int
    mean: float
    low: float
    high: float
    majority_baseline: float | None = None
    text_only_baseline: float | None = None


class Table(FrozenRecord):
    task_type: str
    metric: str
    rows: list[Row]


def _baselines(cases: list[Case]) -> tuple[float | None, float | None]:
    """Outcome cases only: their ruling labels and the facts the target was given."""
    labelled = [
        (str(c.task.inputs.get("facts", "")), f.value)
        for c in cases
        for f in c.reference.facts
        if f.kind == "outcome"
    ]
    if not labelled:
        return None, None
    texts, labels = map(list, zip(*labelled, strict=True))
    return majority_class(labels), text_only(texts, labels)


def build_tables(
    scores: list[Score], cases: list[Case] | None = None, suite_id: str = ""
) -> list[Table]:
    """Never one overall figure: sources and approval states are never averaged together."""
    by_id = {case.id: case for case in cases or []}
    groups: dict[tuple[str, str], dict[tuple[ReferenceSource, Approval], list[Score]]]
    groups = defaultdict(lambda: defaultdict(list))
    for item in scores:
        groups[(item.task_type, item.metric)][(item.reference_source, item.approval)].append(item)
    tables = []
    for (task_type, metric), rows in sorted(groups.items()):
        built = []
        for (source, approval), members in sorted(rows.items()):
            values = [m.value for m in members]
            interval = mean_interval(values, suite_id)
            majority, text = (None, None)
            if metric == "outcome":
                majority, text = _baselines(
                    [by_id[m.case_id] for m in members if m.case_id in by_id]
                )
            built.append(
                Row(
                    reference_source=source,
                    approval=APPROVAL_LABELS[approval],
                    n=len(values),
                    mean=mean(values),
                    low=interval.low,
                    high=interval.high,
                    majority_baseline=majority,
                    text_only_baseline=text,
                )
            )
        tables.append(Table(task_type=task_type, metric=metric, rows=built))
    return tables
