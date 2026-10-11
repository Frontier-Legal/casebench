"""Agents the target tests call: a dict answer, a plain answer, a concurrent one."""

import asyncio
import os
import time

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


async def concurrent(question: str) -> str:
    """Holds its slot long enough for the others to start, and records when it ran."""
    started = time.time()
    await asyncio.sleep(0.3)
    record(
        Step(kind=StepKind.TOOL, name=f"tool-for-{question}", started=started, ended=time.time())
    )
    record(Step(kind=StepKind.LLM, name=f"model-for-{question}"))
    return question


def crashes_on_request(question: str) -> str:
    if question == "crash":
        os._exit(3)
    return f"answered {question}"
