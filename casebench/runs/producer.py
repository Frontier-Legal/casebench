"""What produced a score set: every setting that can move its figures (decision 0035)."""

import hashlib
import inspect
from typing import Any

from pydantic import Field

from casebench import __version__
from casebench.core.case import Case
from casebench.core.model import FrozenRecord
from casebench.judge.prompts import ASKED

READ = ("corpus", "judge")


class MetricUsed(FrozenRecord):
    """A metric's version, and which of the judge and the corpus it reads."""

    version: str
    reads: list[str] = Field(default_factory=list)


class JudgeUsed(FrozenRecord):
    provider: str
    model: str
    family: str
    candidates: int = Field(description="Search results the judge matches a citation against.")


class Producer(FrozenRecord):
    """The first line of every score set, and a copy in its report."""

    # Read when a record is made, so the version is no default in the format's schema, which
    # would change with every release.
    casebench_version: str = Field(default_factory=lambda: __version__)
    metrics: dict[str, MetricUsed]
    judges: list[JudgeUsed] = Field(default_factory=list)
    prompts: dict[str, str] = Field(
        default_factory=dict, description="The SHA-256 of each prompt the judge is asked."
    )
    corpora: dict[str, str] = Field(
        default_factory=dict, description="Each corpus's name and the key of its settings."
    )
    extracted_by: list[str] = Field(
        default_factory=list, description="The models that wrote the cases' answer keys."
    )


def reads(metric: Any) -> list[str]:
    """What a metric was built with, read from its constructor as the loader reads it."""
    parameters = inspect.signature(type(metric)).parameters
    return [name for name in READ if name in parameters]


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def producer_for(
    metrics: list[Any],
    cases: list[Case],
    judges: list[JudgeUsed] | None = None,
    corpora: dict[str, str] | None = None,
) -> Producer:
    return Producer(
        metrics={m.name: MetricUsed(version=m.version, reads=reads(m)) for m in metrics},
        judges=judges or [],
        prompts={name: digest(text) for name, text in ASKED.items()} if judges else {},
        corpora=corpora or {},
        extracted_by=sorted(
            {model for c in cases if c.provenance for model in c.provenance.extracted_by}
        ),
    )
