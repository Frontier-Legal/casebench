"""Send one sample case to the configured target, captured the way a run captures it."""

from casebench.capture.session import session_for
from casebench.config import CasebenchConfig, target_of
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import Result
from casebench.runs.runner import ask
from casebench.targets.load import target_from_config

SAMPLE_QUESTION = "What is the time limit for appealing a first-instance civil judgment?"


async def send_sample(config: CasebenchConfig, question: str = SAMPLE_QUESTION) -> Result:
    agent = target_from_config(target_of(config))
    capture = session_for(config.capture, config.corpora)
    sample = Case(
        id="target-check",
        task=Task.model_validate({"type": "qa", "question": question}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )
    await capture.start()
    try:
        await agent.start()
        try:
            return await ask(sample, agent, capture)
        finally:
            await agent.stop()
    finally:
        await capture.stop()
