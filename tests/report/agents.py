"""Agents that answer outcome cases: always the same ruling, or the ruling the facts hint at."""

import os
from pathlib import Path


def _count() -> None:
    """Each call leaves a line in the file the test names, so the test can count calls."""
    calls = os.environ.get("CASEBENCH_TEST_CALLS")
    if calls:
        with Path(calls).open("a", encoding="utf-8") as out:
            out.write("call\n")


def upheld(question: str, facts: str) -> str:
    _count()
    return "The decision is upheld."


def from_facts(question: str, facts: str) -> str:
    """Right whenever the facts mention an appeal, which is how the test suite is written."""
    _count()
    return "Reversed." if "appeal" in facts else "Upheld."


def careful(question: str, facts: str) -> str:
    """As from_facts, except it notices that a late appeal changes nothing."""
    _count()
    return "Upheld." if "late" in facts else from_facts(question, facts)
