"""Golden data in the workbench's form: a case as the fields a lawyer writes, and back (0052).

The fields are the spreadsheet's for the case's task (decision 0049), so a case written in the
form and one written in a spreadsheet are built the same way.
"""

from pydantic import BaseModel

from casebench.cases.rows import written_case
from casebench.cases.sheet import ID, PRACTICE_AREA, columns, task_names, task_type
from casebench.core.case import Approval, Case, Evidence

# Where a fact the form wrote is said to come from.
FORM = "workbench"


class FieldChange(BaseModel):
    field: str
    before: str
    after: str


def fields_of(task: str) -> list[str]:
    """The form's fields for a task: its inputs, then what the lawyer writes for the reference."""
    return [name for name in columns(task_type(task)) if name != ID]


def editable(case: Case) -> bool:
    """A case of a task type Casebench has a form for."""
    return case.task.type in task_names()


def _text(value: object) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{name}: {text}" for name, text in value.items())
    return "" if value is None else str(value)


def cells_of(case: Case) -> dict[str, str]:
    """The case's fields as the form shows them; every criterion is a key point with its
    weight, such as `+5 Concludes the dismissal is invalid`."""
    wanted = fields_of(case.task.type)
    facts = case.reference.facts
    by_kind: dict[str, list[str]] = {}
    for fact in facts:
        if fact.kind == "issue":
            by_kind.setdefault("issues", []).append(f"{fact.evidence.anchor}: {fact.value}")
        elif fact.kind == "expected":
            by_kind.setdefault("expected", []).append(f"{fact.id}: {fact.value}")
        else:
            by_kind.setdefault(fact.kind, []).append(fact.value)
    cells = {
        "reference answer": "\n".join(by_kind.get("answer", [])),
        "outcome": "\n".join(by_kind.get("outcome", [])),
        "statutes": "\n".join(by_kind.get("statute", [])),
        "precedents": "\n".join(by_kind.get("precedent", [])),
        "issues": "\n".join(by_kind.get("issues", [])),
        "expected": "\n".join(by_kind.get("expected", [])),
        "key points": "\n".join(f"{c.weight:+d} {c.text}" for c in case.reference.criteria),
    }
    cells |= {name: _text(value) for name, value in case.task.inputs.items()}
    cells[PRACTICE_AREA] = case.practice_area or ""
    return {name: cells.get(name, "") for name in wanted}


def changes(before: dict[str, str], after: dict[str, str]) -> list[FieldChange]:
    """The fields whose text differs, whitespace at the ends aside."""
    return [
        FieldChange(field=name, before=before.get(name, ""), after=after.get(name, ""))
        for name in dict.fromkeys([*before, *after])
        if before.get(name, "").strip() != after.get(name, "").strip()
    ]


def new_case(
    task: str,
    cells: dict[str, str],
    case_id: str,
    author: str,
    approval: Approval = Approval.DRAFT,
) -> Case:
    """A case written in the form: approved by its author, or a draft until a second editor
    approves it (decisions 0052, 0053)."""
    return written_case(
        task,
        cells,
        author,
        case_id=case_id,
        written=Evidence(doc=FORM, note=f"written by {author}"),
        where=f"case {case_id}",
        read=lambda text: text,
        approval=approval,
    )


def revised(case: Case, cells: dict[str, str], author: str) -> Case:
    """The case with the form's fields. A fact the lawyer left as it was keeps its evidence
    and the corpus document it resolved to; the case keeps its id, source, author, metrics,
    provenance, approval and approver, and takes the form's practice area."""
    rebuilt = written_case(
        case.task.type,
        cells,
        author,
        case_id=case.id,
        written=Evidence(doc=FORM, note=f"edited by {author}"),
        where=f"case {case.id}",
        read=lambda text: text,
        approval=case.approval,
    )
    kept = {(f.kind, f.value): f for f in case.reference.facts}
    facts = [
        f.model_copy(update={"evidence": old.evidence, "document_id": old.document_id})
        if (old := kept.get((f.kind, f.value)))
        else f
        for f in rebuilt.reference.facts
    ]
    reference = rebuilt.reference.model_copy(
        update={
            "facts": facts,
            "source": case.reference.source,
            "author": case.reference.author or author,
        }
    )
    metrics = list(dict.fromkeys([*rebuilt.metrics, *case.metrics]))
    return case.model_copy(
        update={
            "task": rebuilt.task,
            "reference": reference,
            "metrics": metrics,
            "practice_area": rebuilt.practice_area,
        }
    )
