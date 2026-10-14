"""The checks a config calls for: each passed, failed, or out of reach from this machine."""

import ast
import asyncio
import importlib.util
import socket
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import httpx2

from casebench.capture.step import StepKind
from casebench.config import CasebenchConfig
from casebench.corpus.check import SAMPLE_SIZE, check
from casebench.corpus.corpora import Corpora
from casebench.corpus.interface import ListingNotSupported
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.providers.call import KeyRefused
from casebench.providers.interface import Message
from casebench.providers.settings import settings_of
from casebench.setup.catalog import installed
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


# The step that fixes each part, in words a person or a coding agent acts on (0044).
NEXT_TARGET = (
    "make the target answer: its function must run as the project's own start runs it, with the "
    "settings the agent reads loaded first"
)
NEXT_MODEL = "check the model's id and the key casebench.yaml names for it under `keys`"
NEXT_REACH = "run this where the service is reachable"
NEXT_PLUGIN = "install the package that provides it"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str = ""
    next: str = ""

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


def _failure(name: str, error: Exception, next_step: str) -> Check:
    if unreachable(error):
        return Check(name, Status.UNREACHABLE, f"{type(error).__name__}: {error}", NEXT_REACH)
    return Check(name, Status.FAILED, f"{type(error).__name__}: {error}", next_step)


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
    for name, corpus in config.corpora.items():
        label = f"corpus {name}" if len(config.corpora) > 1 else "corpus"
        named.append((label, "connector", corpus.connector, corpus.connector_source))
    for name, model in models_of(config):
        named.append((name, "provider", model.provider, model.provider_source))
    for name, kind, plugin, source in named:
        try:
            registry.load(kind_named(kind), plugin, source)
        except Exception as error:
            checks.append(Check(name, Status.FAILED, str(error), NEXT_PLUGIN))
    for name, model in models_of(config):
        if not any(c.name == name for c in checks):
            checks += _model_request(name, model)
    if config.target is not None and config.target.get("type") == "python":
        problem = _entry_defined(str(config.target.get("entry", "")))
        if problem:
            checks.append(Check("target", Status.FAILED, problem, NEXT_TARGET))
    return checks


def models_of(config: CasebenchConfig) -> list[tuple[str, JudgeConfig]]:
    """Every model Casebench calls itself: the judges and the extraction models."""
    names = ["judge", "second judge"]
    models = [(names[n], model) for n, model in enumerate(config.judges)]
    if config.extract is not None:
        models += [(f"extract{n}", m) for n, m in enumerate(config.extract.models, start=1)]
    return models


def _model_request(name: str, model: JudgeConfig) -> list[Check]:
    """Build one request without sending it, so a missing option shows here. A provider that
    calls its own SDK is checked for that SDK instead."""
    try:
        provider = Judge(model).provider
        missing = [p for p in getattr(provider, "packages", ()) if not installed(p)]
        if missing:
            listed = ", ".join(missing)
            installs = f"install {listed} in this environment"
            return [Check(name, Status.FAILED, f"{listed} is not installed here", installs)]
        if getattr(provider, "complete", None) is None:
            messages = [Message(role="system", content=JUDGE_SYSTEM)]
            provider.request(messages, model.model, "not-sent")
    except Exception as error:
        return [Check(name, Status.FAILED, str(error), NEXT_MODEL)]
    return []


def _corpus(corpora: Corpora, name: str, queries: list[str], size: int) -> Check:
    """Opening the corpus is part of the check, so a store out of reach is reported as such."""
    label = f"corpus {name}" if len(corpora.names) > 1 else "corpus"
    try:
        report = check(corpora.named(name), queries, size)
    except ListingNotSupported:
        searched = "add it again with `casebench corpus add --probe TEXT`, or pass --query TEXT"
        return Check(label, Status.FAILED, "the store cannot list documents", searched)
    except Exception as error:
        return _failure(label, error, "check the corpus's address, paths and key")
    if report.failures or report.missing:
        missing = f"missing {', '.join(report.missing)}" if report.missing else ""
        failed = f"{len(report.failures)} fetches failed" if report.failures else ""
        mapped = "map each missing field with `casebench corpus add --field NAME=JSONPATH`"
        return Check(label, Status.FAILED, "; ".join(filter(None, (missing, failed))), mapped)
    sampled = f"{report.sampled} document{'s' if report.sampled != 1 else ''} sampled"
    return Check(label, Status.PASSED, sampled)


def _target(config: CasebenchConfig) -> Check:
    try:
        result = asyncio.run(send_sample(config))
    except Exception as error:
        return _failure("target", error, NEXT_TARGET)
    if result.error:
        # The runner records a failure as "<exception type>: <message>".
        if result.error.startswith(CONNECTION_FAILURES):
            return Check("target", Status.UNREACHABLE, result.error, NEXT_REACH)
        return Check("target", Status.FAILED, result.error, NEXT_TARGET)
    if not [step for step in result.steps if step.kind is not StepKind.GAP]:
        # Answering is what the check needs; the funnel needs the calls (decision 0044).
        quiet = (
            "answered, but no call was recorded, so a report cannot say where an authority was "
            "lost; a Python target records calls made through httpx2, httpx or requests"
        )
        return Check("target", Status.PASSED, quiet)
    calls = [step for step in result.steps if step.kind is not StepKind.GAP]
    said = f"{len(calls)} call{'s' if len(calls) != 1 else ''} recorded"
    return Check("target", Status.PASSED, f"answered, {said}")


def _refused(error: BaseException) -> bool:
    """Whether a provider refused the key, anywhere in the chain of causes."""
    seen: BaseException | None = error
    while seen is not None:
        if isinstance(seen, KeyRefused):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


def model_check(name: str, model: JudgeConfig) -> Check:
    """Asked with its settings, so the check says whether the provider takes them (0038)."""
    settings = settings_of(model.options)
    shown = ", ".join(f"{key}={value}" for key, value in settings.items())
    try:
        Judge(model).ask(JUDGE_SYSTEM, JUDGE_QUESTION)
    except Exception as error:
        named = getattr(Judge(model).provider, "api_key_env", None)
        refused = (
            f"the provider refused the key: check that {named} holds a key for this provider; "
            f"`casebench keys {named}` says where it is read from"
            if named
            else "the provider refused the credentials it found here"
        )
        failed = _failure(name, error, refused if _refused(error) else NEXT_MODEL)
        if settings and failed.status is Status.FAILED and not _refused(error):
            refused = f"refused the call with {shown}: {failed.detail}"
            failed = Check(name, Status.FAILED, refused, f"drop {shown} from its options")
        return failed
    accepted = f", accepting {shown}" if settings else ""
    return Check(name, Status.PASSED, f"{model.provider} {model.model} answered{accepted}")


def _probe(probe: str | None) -> list[str]:
    """The search a corpus was added with, run when no other is given (decision 0044)."""
    return [probe] if probe else []


def live(
    config: CasebenchConfig, queries: list[str] | None = None, size: int = SAMPLE_SIZE
) -> list[Check]:
    """One check for each part the config names: the corpus, the target, each model."""
    checks = []
    corpora = Corpora(config.corpora)
    checks += [
        _corpus(corpora, name, queries or _probe(config.corpora[name].probe), size)
        for name in corpora.names
    ]
    if config.target is not None:
        checks.append(_target(config))
    checks += [model_check(name, model) for name, model in models_of(config)]
    return checks
