"""A document's clauses by number, and which an edit changed (decision 0049)."""

import difflib
import re

from casebench.core.case import Case

ISSUE = "issue"
PREAMBLE = "preamble"
# A line that starts with a clause number, such as "4." or "9.2", followed by its text.
NUMBERED = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?(?=\s|\)|$)")


def clauses(text: str) -> dict[str, str]:
    """Each clause's text under its number; text before the first number is the preamble. A
    number used twice gets its place as a suffix, such as "4 (2)"."""
    out: dict[str, list[str]] = {}
    current = PREAMBLE
    for line in text.splitlines():
        found = NUMBERED.match(line)
        if found:
            current = found.group(1)
            place = 2
            while current in out:
                current = f"{found.group(1)} ({place})"
                place += 1
        out.setdefault(current, []).append(line)
    return {number: "\n".join(lines) for number, lines in out.items()}


def _plain(text: str) -> str:
    return " ".join(text.split())


def changed(before: str, after: str) -> list[str]:
    """The clauses of `before` whose text differs in `after`, whitespace aside, in order; a
    clause `after` no longer has is changed too."""
    edited = clauses(after)
    return [
        number
        for number, text in clauses(before).items()
        if _plain(text) != _plain(edited.get(number, ""))
    ]


def diff(before: str, after: str, number: str) -> str:
    old, new = clauses(before).get(number, ""), clauses(after).get(number, "")
    lines = difflib.unified_diff(
        old.splitlines(), new.splitlines(), f"clause {number}", f"clause {number}", lineterm=""
    )
    return "\n".join(lines)


def issues(case: Case) -> list[tuple[str, str]]:
    """Each issue the reference lists, as its clause number and what is wrong there."""
    return [
        (f.evidence.anchor or PREAMBLE, f.value) for f in case.reference.facts if f.kind == ISSUE
    ]
