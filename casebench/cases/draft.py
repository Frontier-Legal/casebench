"""Draft one case from one decision with one model, and say what the draft took (0039)."""

import time
from dataclasses import dataclass

from casebench.corpus.record import DecisionRecord
from casebench.extract.prompt import EXTRACT, decision_prompt
from casebench.extract.reading import Reading, read_reply
from casebench.judge.client import Judge

DRAFT = f"""{EXTRACT}
Add one more key, "question": the question a lawyer would put to a legal AI system about this \
dispute, in the decision's language, without its answer."""


@dataclass(frozen=True)
class Draft:
    """What the model read in the decision, with only the quotes really in its text."""

    decision: DecisionRecord
    question: str
    reading: Reading
    model: str
    seconds: float
    cost: float | None
    tokens: int


def draft(model: Judge, decision: DecisionRecord) -> Draft:
    started = time.perf_counter()
    before = model.input_tokens + model.output_tokens
    reply = model.ask(DRAFT, decision_prompt(decision.text))
    question = reply.get("question") if isinstance(reply, dict) else None
    return Draft(
        decision=decision,
        question=question.strip() if isinstance(question, str) else "",
        reading=read_reply(decision.text, reply),
        model=f"{model.config.provider}/{model.config.model}",
        seconds=time.perf_counter() - started,
        cost=model.cost,
        tokens=model.input_tokens + model.output_tokens - before,
    )
