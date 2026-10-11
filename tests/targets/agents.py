"""Agents the target tests call: a dict answer, a plain answer, a concurrent one."""

import asyncio

from casebench.capture.context import record
from casebench.capture.step import Step, StepKind


def answer(question: str, facts: str) -> dict:
    record(Step(kind=StepKind.RETRIEVAL, name="search", doc_ids_out=["tr-1"]))
    return {
        "answer": f"Asked: {question} Given: {facts}",
        "citations": ["E2023/1-K2024/2"],
        "documents": ["tr-1"],
    }


def plain(question: str) -> str:
    return "The court relied on E.2023/1 K.2024/2 and E.2022/7 K.2023/9."


def chunks(question: str):
    yield "first "
    yield "second"


class Gate:
    """Lets every case through once `width` of them are inside at the same time."""

    def __init__(self, width: int) -> None:
        self.width, self.inside, self.peak = width, 0, 0
        self.full = asyncio.Event()


gate: Gate | None = None


async def concurrent(question: str) -> str:
    assert gate is not None
    gate.inside += 1
    gate.peak = max(gate.peak, gate.inside)
    if gate.inside >= gate.width:
        gate.full.set()
    await gate.full.wait()
    record(Step(kind=StepKind.TOOL, name=f"tool-for-{question}"))
    await asyncio.sleep(0)
    record(Step(kind=StepKind.LLM, name=f"model-for-{question}"))
    gate.inside -= 1
    return question
