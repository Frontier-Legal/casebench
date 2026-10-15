"""Answers from a tool Casebench cannot reach: a suite's questions out as CSV, the answers back in.

The answers are scored as a connected run's are (decision 0061).
"""

import csv
from pathlib import Path
from typing import Any

from casebench.core.case import Case
from casebench.runs.log import Result

CASE, REPEAT, ANSWER = "case_id", "repeat", "answer"
TARGET = "offline"


class AnswersError(ValueError):
    """A sheet of answers that cannot be read; the message names the row."""


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{name}: {text}" for name, text in value.items())
    return "" if value is None else str(value)


def write_questions(cases: list[Case], path: Path) -> int:
    """One row per case: its id, the repeat, each input the case gives, and an empty answer."""
    inputs = sorted({name for case in cases for name in case.task.inputs})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([CASE, REPEAT, *inputs, ANSWER])
        for case in cases:
            writer.writerow(
                [case.id, 0, *(_text(case.task.inputs.get(name)) for name in inputs), ""]
            )
    return len(cases)


def is_answers(path: Path) -> bool:
    """A CSV whose header names the case and the answer."""
    if path.suffix.lower() != ".csv" or not path.is_file():
        return False
    with path.open(encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), [])
    return CASE in header and ANSWER in header


def read_answers(path: Path, cases: list[Case]) -> tuple[list[Result], list[str]]:
    """The answered rows as results; the cases left unanswered, by id."""
    known = {case.id for case in cases}
    results: dict[tuple[str, int], Result] = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for number, row in enumerate(csv.DictReader(stream), start=2):
            case_id = (row.get(CASE) or "").strip()
            answer = (row.get(ANSWER) or "").strip()
            if not case_id and not answer:
                continue
            if case_id not in known:
                raise AnswersError(f"{path.name}, row {number}: the suite has no case {case_id!r}")
            repeat = (row.get(REPEAT) or "0").strip() or "0"
            if not repeat.isdigit():
                raise AnswersError(f"{path.name}, row {number}: repeat {repeat!r} is no number")
            if answer:
                results[(case_id, int(repeat))] = Result(
                    case_id=case_id, repeat=int(repeat), output=answer
                )
    answered = {case_id for case_id, _ in results}
    return list(results.values()), sorted(known - answered)
