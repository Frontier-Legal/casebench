"""The demo's agent: it answers each question with the answer recorded for it."""

import json

from casebench.demo import PROJECT


def answer(question: str) -> str:
    recorded = json.loads((PROJECT / "answers.json").read_text(encoding="utf-8"))
    return recorded[question]
