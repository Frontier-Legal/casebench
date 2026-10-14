"""Send one sample case to the configured target, captured the way a run captures it."""

from casebench.capture.session import session_for
from casebench.config import CasebenchConfig, target_of
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import Result
from casebench.runs.runner import ask
from casebench.targets.load import target_from_config

# What a check asks: an answer shows the agent starts and answers, and a greeting asks for
# no research, so a slow agent answers it quickly and spends little (decision 0045).
GREETING = "Hi. How are you?"


async def send_sample(config: CasebenchConfig, question: str | None = None) -> Result:
    """One question, the greeting unless another is given, asked once, with the agent's
    calls recorded as a run records them."""
    agent = target_from_config(target_of(config))
    capture = session_for(config.capture, config.corpora)
    sample = Case(
        id="target-check",
        task=Task.model_validate({"type": "qa", "question": question or GREETING}),
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
