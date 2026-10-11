"""The checks a config calls for: each passed, failed, or out of reach from this machine."""

import ast
import asyncio
import importlib.util
import socket
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx2

from casebench.config import CasebenchConfig
from casebench.corpus.binding import Corpus
from casebench.corpus.check import SAMPLE_SIZE, check
from casebench.corpus.interface import ListingNotSupported
from casebench.judge.client import Judge
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.providers.interface import Message
from casebench.targets.sample import send_sample

JUDGE_SYSTEM = "Reply with JSON only."
JUDGE_QUESTION = 'Reply with {"ok": true}.'
CONNECTION_FAILURES = (
    "ConnectError:",
    "ConnectTimeout:",
    "ConnectionRefusedError:",
    "URLError:",
    "gaierror:",
)


class Status(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    UNREACHABLE = "not reachable from here"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str = ""

    def line(self) -> str:
        return f"{self.name:<8} {self.status.value}" + (f": {self.detail}" if self.detail else "")


def unreachable(error: BaseException) -> bool:
    """A connection that could not be made, anywhere in the chain or the group."""
    seen: list[BaseException] = [error]
    while seen:
        current = seen.pop()
        if isinstance(current, httpx2.TransportError | ConnectionError | socket.gaierror):
            return True
        if isinstance(current, BaseExceptionGroup):
            seen += list(current.exceptions)
        seen += [e for e in (current.__cause__, current.__context__) if e is not None]
    return False


def _failure(name: str, error: Exception) -> Check:
    status = Status.UNREACHABLE if unreachable(error) else Status.FAILED
    return Check(name, status, f"{type(error).__name__}: {error}")


def _entry_defined(entry: str) -> str | None:
    """Whether a Python entry names a function that exists, read without running the module."""
    location, _, function = entry.rpartition(":")
    if not location:
        location, function = entry, "answer"
    if location.endswith(".py"):
        path = Path(location)
        if not path.is_file():
            return f"{path} does not exist"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        }
        names |= {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        return None if function in names else f"{path} defines no {function!r}"
    try:
        found = importlib.util.find_spec(location)
    except ModuleNotFoundError:
        found = None
    return None if found else f"no module named {location!r} is importable here"


def offline(config: CasebenchConfig) -> list[Check]:
    """What needs no network: every plugin the config names loads, and a Python entry exists."""
    checks = []
    named = []
    if config.target is not None:
        named.append(("target", "target", str(config.target.get("type")), None))
    if config.corpus is not None:
        source = config.corpus.connector_source
        named.append(("corpus", "connector", config.corpus.connector, source))
    if config.judge is not None:
        named.append(("judge", "provider", config.judge.provider, config.judge.provider_source))
    for name, kind, plugin, source in named:
        try:
            registry.load(kind_named(kind), plugin, source)
        except Exception as error:
            checks.append(Check(name, Status.FAILED, str(error)))
    if config.judge is not None and not checks:
        checks += _judge_request(config)
    if config.target is not None and config.target.get("type") == "python":
        problem = _entry_defined(str(config.target.get("entry", "")))
        if problem:
            checks.append(Check("target", Status.FAILED, problem))
    return checks


def _judge_request(config: CasebenchConfig) -> list[Check]:
    """Build one request without sending it, so a missing provider option shows here."""
    assert config.judge is not None
    messages = [Message(role="system", content=JUDGE_SYSTEM), Message(role="user", content="")]
    try:
        Judge(config.judge).provider.request(messages, config.judge.model, "not-sent")
    except Exception as error:
        return [Check("judge", Status.FAILED, str(error))]
    return []


def _corpus(config: CasebenchConfig, queries: list[str], size: int) -> Check:
    assert config.corpus is not None
    try:
        report = check(Corpus(config.corpus), queries, size)
    except ListingNotSupported:
        return Check("corpus", Status.FAILED, "the store cannot list documents; pass --query")
    except Exception as error:
        return _failure("corpus", error)
    if report.failures or report.missing:
        missing = f"missing {', '.join(report.missing)}" if report.missing else ""
        failed = f"{len(report.failures)} fetches failed" if report.failures else ""
        return Check("corpus", Status.FAILED, "; ".join(filter(None, (missing, failed))))
    return Check("corpus", Status.PASSED, f"{report.sampled} documents sampled")


def _target(config: CasebenchConfig) -> Check:
    try:
        result = asyncio.run(send_sample(config))
    except Exception as error:
        return _failure("target", error)
    if result.error:
        # The runner records a failure as "<exception type>: <message>".
        unreachable = result.error.startswith(CONNECTION_FAILURES)
        return Check("target", Status.UNREACHABLE if unreachable else Status.FAILED, result.error)
    return Check("target", Status.PASSED, f"answered, {len(result.steps)} steps captured")


def _judge(config: CasebenchConfig) -> Check:
    assert config.judge is not None
    try:
        Judge(config.judge).ask(JUDGE_SYSTEM, JUDGE_QUESTION)
    except Exception as error:
        return _failure("judge", error)
    return Check("judge", Status.PASSED, f"{config.judge.provider} {config.judge.model} answered")


def live(
    config: CasebenchConfig, queries: list[str] | None = None, size: int = SAMPLE_SIZE
) -> list[Check]:
    """One check for each part the config names: the corpus, the target, the judge."""
    checks = []
    if config.corpus is not None:
        checks.append(_corpus(config, queries or [], size))
    if config.target is not None:
        checks.append(_target(config))
    if config.judge is not None:
        checks.append(_judge(config))
    return checks
