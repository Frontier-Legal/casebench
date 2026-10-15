"""Turn what a lawyer wrote, a spreadsheet row or the workbench's form, into a case (0049, 0052)."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from casebench.cases.sheet import ID, Row, SheetError, read_document, task_type
from casebench.core.case import (
    Approval,
    Case,
    Criterion,
    Evidence,
    Fact,
    Provenance,
    Reference,
    ReferenceSource,
    Task,
)

ANSWER = "answer-1"
KEY_POINT = "key point"
CRITERIA = "criteria"


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _named(text: str, where: str, column: str) -> list[tuple[str, str]]:
    """Lines such as `9.2: Uncapped indemnity` or `party_a: Acme`."""
    out = []
    for line in _lines(text):
        name, colon, value = line.partition(":")
        if not colon or not name.strip() or not value.strip():
            raise SheetError(f"{where}: {column} wants name: value, not {line!r}")
        out.append((name.strip(), value.strip()))
    return out


def _is_weight(word: str) -> bool:
    """A signed whole number, such as +5 or -4."""
    digits = word[1:] if word[:1] in "+-" else word
    return digits.isascii() and digits.isdigit()


def _weighted(line: str, where: str) -> tuple[int, str]:
    """A key point's weight, such as +5 or -4, before its text; without one it weighs 1. Split
    on whitespace, never matched by a pattern, so a line of any length is read in one pass."""
    parts = line.split(maxsplit=1)
    if len(parts) == 2 and _is_weight(parts[0]):
        weight, text = int(parts[0]), parts[1]
    else:
        weight, text = 1, line
    if weight == 0:
        raise SheetError(f"{where}: the key point {text!r} weighs 0, so never counts")
    return weight, text.strip()


def _inputs(
    cells: dict[str, str], inputs: tuple[str, ...], where: str, read: Callable[[str], str]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in inputs:
        value = cells.get(name, "")
        if not value:
            continue
        if name == "document":
            out[name] = read(value)
        elif name == "fields":
            out[name] = dict(_named(value, where, name))
        else:
            out[name] = value
    return out


def written_case(
    task_name: str,
    cells: dict[str, str],
    author: str,
    *,
    case_id: str,
    written: Evidence,
    where: str,
    read: Callable[[str], str],
    approval: Approval,
) -> Case:
    """Each key point is a criterion in the lawyer's words, from a fact whose evidence is
    `written`; the reference answer is evidence for each, and alone makes no criterion. `read`
    turns the document cell into the document's text."""
    task = task_type(task_name)
    facts: list[Fact] = []
    criteria: list[Criterion] = []
    if cells.get("reference answer"):
        facts.append(
            Fact(id=ANSWER, kind="answer", value=cells["reference answer"], evidence=written)
        )
    if cells.get("outcome"):
        facts.append(Fact(id="outcome-1", kind="outcome", value=cells["outcome"], evidence=written))
    answer = [ANSWER] if cells.get("reference answer") else []
    for n, line in enumerate(_lines(cells.get("key points", "")), start=1):
        weight, text = _weighted(line, where)
        facts.append(Fact(id=f"key-point-{n}", kind=KEY_POINT, value=text, evidence=written))
        criteria.append(
            Criterion(
                id=f"k{n}", text=text, weight=weight, derived_from=[f"key-point-{n}", *answer]
            )
        )
    for kind, column in (("statute", "statutes"), ("precedent", "precedents")):
        facts += [
            Fact(id=f"{kind}-{n}", kind=kind, value=value, evidence=written)
            for n, value in enumerate(_lines(cells.get(column, "")), start=1)
        ]
    for n, (clause, issue) in enumerate(_named(cells.get("issues", ""), where, "issues"), 1):
        evidence = written.model_copy(update={"anchor": clause})
        facts.append(Fact(id=f"issue-{n}", kind="issue", value=issue, evidence=evidence))
    expected = _named(cells.get("expected", ""), where, "expected")
    facts += [
        Fact(id=name, kind="expected", value=value, evidence=written) for name, value in expected
    ]
    metrics = list(task.default_metrics)
    if criteria and CRITERIA not in metrics:
        metrics.append(CRITERIA)
    try:
        reference = Reference(
            source=ReferenceSource.LAWYER, facts=facts, criteria=criteria, author=author
        )
    except ValueError as failure:
        raise SheetError(f"{where}: {failure}") from None
    inputs = _inputs(cells, task.input_fields, where, read)
    return Case(
        id=case_id,
        task=Task.model_validate({"type": task_name, **inputs}),
        reference=reference,
        metrics=metrics,
        provenance=Provenance(builder="lawyer"),
        approval=approval,
    )


def row_case(row: Row, source: Path, author: str) -> Case:
    """A spreadsheet row, approved by the lawyer who wrote it (decision 0049). An issue's
    evidence is its clause in the document the row names."""
    case = written_case(
        row.task,
        row.cells,
        author,
        case_id=row.cells.get(ID) or f"{source.stem}-{row.number}",
        written=Evidence(doc=source.name, anchor=f"row {row.number}", note=f"written by {author}"),
        where=row.where(source),
        read=lambda value: read_document(source.parent / value),
        approval=Approval.APPROVED,
    )
    document = row.cells.get("document") or source.name
    facts = [
        f.model_copy(update={"evidence": f.evidence.model_copy(update={"doc": document})})
        if f.kind == "issue"
        else f
        for f in case.reference.facts
    ]
    return case.model_copy(update={"reference": case.reference.model_copy(update={"facts": facts})})
