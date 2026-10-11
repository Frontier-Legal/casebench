"""The python target: answer each case in one of N worker processes running the agent."""

import asyncio
import os
import sys
from collections.abc import Mapping
from typing import Any

from casebench.capture.context import current_traceparent, record, set_worker
from casebench.capture.session import PROXY, PROXY_VARIABLES
from casebench.capture.step import Step
from casebench.core.model import Record
from casebench.targets.answer import Answer, CitationParser, to_answer
from casebench.targets.builtin.python.framing import read_message_async, send
from casebench.targets.interface import TargetDidNotStart

WORKER_MODULE = "casebench.targets.builtin.python.worker"


class WorkerDied(RuntimeError):
    """The agent's process ended while answering a case."""


class AgentDidNotStart(TargetDidNotStart):
    """The agent could not be loaded in a worker; the run stops before its first case."""


class AgentError(RuntimeError):
    """The agent raised while answering a case; the message is the agent's own."""


class PythonConfig(Record):
    type: str = "python"
    entry: str
    max_concurrency: int = 1


def worker_environment(worker: int) -> dict[str, str]:
    """The run's environment, with each proxy variable under this worker's own path."""
    env = dict(os.environ)
    proxy = env.get(PROXY)
    for name in filter(None, env.get(PROXY_VARIABLES, "").split(",")):
        if proxy and name in env:
            env[name] = env[name].replace(proxy, f"{proxy}/w/{worker}", 1)
    return env


class Worker:
    def __init__(self, number: int, entry: str) -> None:
        self.number, self.entry = number, entry
        self.process: asyncio.subprocess.Process | None = None

    async def start(self) -> None:
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            WORKER_MODULE,
            self.entry,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=worker_environment(self.number),
        )
        assert self.process.stdout is not None
        hello = await read_message_async(self.process.stdout)
        if not hello or not hello.get("ready"):
            await self.process.wait()
            reason = (hello or {}).get("error", f"exit code {self.process.returncode}")
            raise AgentDidNotStart(f"the agent did not start: {reason}")

    async def ask(self, case_id: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
        process = self.process
        assert process is not None and process.stdin and process.stdout
        try:
            message = {
                "case": case_id,
                "inputs": dict(inputs),
                "traceparent": current_traceparent(),
            }
            await send(process.stdin, message)
            reply = await read_message_async(process.stdout)
        except (BrokenPipeError, ConnectionResetError, asyncio.IncompleteReadError):
            reply = None
        if reply is None:
            code = await process.wait()
            await self.start()
            raise WorkerDied(f"the agent's process exited with {code} during this case")
        return reply

    async def stop(self) -> None:
        if self.process is not None and self.process.stdin is not None:
            self.process.stdin.close()
            await self.process.wait()
            self.process = None


class Target:
    def __init__(self, **config: Any) -> None:
        self.config = PythonConfig.model_validate(config)
        self.workers: list[Worker] = []
        self.idle: asyncio.Queue[Worker] = asyncio.Queue()
        self.cases = 0

    async def start(self, slots: int = 1) -> None:
        """One worker per parallel slot, each importing the agent once."""
        count = max(slots, self.config.max_concurrency)
        self.idle = asyncio.Queue()
        self.workers = [Worker(n, self.config.entry) for n in range(count)]
        await asyncio.gather(*(worker.start() for worker in self.workers))
        for worker in self.workers:
            self.idle.put_nowait(worker)

    async def answer(
        self, inputs: Mapping[str, Any], parse_citations: CitationParser | None = None
    ) -> Answer:
        if not self.workers:
            await self.start()
        worker = await self.idle.get()
        self.cases += 1
        set_worker(str(worker.number))
        try:
            reply = await worker.ask(f"case-{self.cases}", inputs)
        finally:
            self.idle.put_nowait(worker)
        for step in reply.get("steps", []):
            record(Step.model_validate(step))
        if "error" in reply:
            raise AgentError(reply["error"])
        return to_answer(reply["value"], parse_citations)

    async def stop(self) -> None:
        await asyncio.gather(*(worker.stop() for worker in self.workers))
        self.workers = []
