"""Send one sample case to the configured target, captured the way a run captures it."""

from casebench.capture.session import session_for
from casebench.config import CasebenchConfig, target_of
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import Result
from casebench.runs.runner import ask
from casebench.targets.load import target_from_config

SAMPLE_QUESTION = "What is the time limit for appealing a first-instance civil judgment?"


def sample_question(config: CasebenchConfig) -> str:
    """The search a corpus was added with, which is a question in the corpus's own language and
    field, or else a general one (decision 0044)."""
    return next((c.probe for c in config.corpora.values() if c.probe), SAMPLE_QUESTION)


async def send_case(config: CasebenchConfig, case: Case) -> Result:
    """One case, asked once, with its calls recorded as a run records them."""
    agent = target_from_config(target_of(config))
    capture = session_for(config.capture, config.corpora)
    await capture.start()
    try:
        await agent.start()
        try:
            return await ask(case, agent, capture)
        finally:
            await agent.stop()
    finally:
        await capture.stop()


async def send_sample(config: CasebenchConfig, question: str | None = None) -> Result:
    sample = Case(
        id="target-check",
        task=Task.model_validate({"type": "qa", "question": question or sample_question(config)}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )
    return await send_case(config, sample)
