"""Report tables: one per task and metric, split by reference source and approval."""

from collections import defaultdict
from statistics import fmean

from casebench.core.case import Approval, ReferenceSource
from casebench.core.model import FrozenRecord
from casebench.core.score import Score

APPROVAL_LABELS = {Approval.APPROVED: "lawyer-approved", Approval.DRAFT: "unreviewed"}


class Row(FrozenRecord):
    reference_source: ReferenceSource
    approval: str
    n: int
    mean: float


class Table(FrozenRecord):
    task_type: str
    metric: str
    rows: list[Row]


def build_tables(scores: list[Score]) -> list[Table]:
    """Never one overall figure: sources and approval states are never averaged together."""
    groups: dict[tuple[str, str], dict[tuple[ReferenceSource, Approval], list[float]]]
    groups = defaultdict(lambda: defaultdict(list))
    for item in scores:
        groups[(item.task_type, item.metric)][(item.reference_source, item.approval)].append(
            item.value
        )
    return [
        Table(
            task_type=task_type,
            metric=metric,
            rows=[
                Row(
                    reference_source=source,
                    approval=APPROVAL_LABELS[approval],
                    n=len(values),
                    mean=fmean(values),
                )
                for (source, approval), values in sorted(rows.items())
            ],
        )
        for (task_type, metric), rows in sorted(groups.items())
    ]
