"""Turn a spreadsheet row a lawyer filled into an approved case (decision 0049)."""

import re
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
# A key point's weight, such as +5 or -4, before its text.
WEIGHTED = re.compile(r"^([+-]?\d+)\s+(.+)$")
NAMED = re.compile(r"^([^:]+):\s*(.+)$")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _named(text: str, row: Row, source: Path, column: str) -> list[tuple[str, str]]:
    """Lines such as `9.2: Uncapped indemnity` or `party_a: Acme`."""
    out = []
    for line in _lines(text):
        found = NAMED.match(line)
        if not found:
            raise SheetError(f"{row.where(source)}: {column} wants name: value, not {line!r}")
        out.append((found.group(1).strip(), found.group(2).strip()))
    return out


def _weighted(line: str, row: Row, source: Path) -> tuple[int, str]:
    found = WEIGHTED.match(line)
    weight, text = (int(found.group(1)), found.group(2)) if found else (1, line)
    if weight == 0:
        raise SheetError(f"{row.where(source)}: the key point {text!r} weighs 0, so never counts")
    return weight, text.strip()


def _inputs(row: Row, inputs: tuple[str, ...], source: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in inputs:
        value = row.cells.get(name, "")
        if not value:
            continue
        if name == "document":
            out[name] = read_document(source.parent / value)
        elif name == "fields":
            out[name] = dict(_named(value, row, source, name))
        else:
            out[name] = value
    return out


def row_case(row: Row, source: Path, author: str) -> Case:
    """Each key point is a criterion in the lawyer's words, from a fact whose evidence is the
    row; the reference answer is evidence for each, and alone makes no criterion."""
    task = task_type(row.task)
    cells = row.cells
    written = Evidence(doc=source.name, anchor=f"row {row.number}", note=f"written by {author}")
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
        weight, text = _weighted(line, row, source)
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
    document = cells.get("document") or source.name
    for n, (clause, issue) in enumerate(_named(cells.get("issues", ""), row, source, "issues"), 1):
        evidence = Evidence(doc=document, anchor=clause, note=f"written by {author}")
        facts.append(Fact(id=f"issue-{n}", kind="issue", value=issue, evidence=evidence))
    expected = _named(cells.get("expected", ""), row, source, "expected")
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
        raise SheetError(f"{row.where(source)}: {failure}") from None
    inputs = _inputs(row, task.input_fields, source)
    return Case(
        id=cells.get(ID) or f"{source.stem}-{row.number}",
        task=Task.model_validate({"type": row.task, **inputs}),
        reference=reference,
        metrics=metrics,
        provenance=Provenance(builder="lawyer"),
        approval=Approval.APPROVED,
    )
