"""Build the metrics a suite's cases name, with what each needs (a judge, a corpus)."""

import inspect
from typing import Any

from casebench.core.case import Case
from casebench.metrics.base import Metric
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


class MetricNeeds(LookupError):
    """A metric needs a judge or a corpus the config does not have."""


def build(name: str, context: dict[str, Any]) -> Metric:
    factory = registry.load(kind_named("metric"), name)
    wanted = [
        p
        for p in inspect.signature(factory).parameters.values()
        if p.kind is p.KEYWORD_ONLY or (p.kind is p.POSITIONAL_OR_KEYWORD and p.name != "self")
    ]
    missing = [p.name for p in wanted if p.default is p.empty and context.get(p.name) is None]
    if missing:
        raise MetricNeeds(f"the {name} metric needs {', '.join(missing)} in the config")
    return factory(**{p.name: context[p.name] for p in wanted if p.name in context})


def metrics_for(cases: list[Case], context: dict[str, Any]) -> list[Metric]:
    names = sorted({name for case in cases for name in case.metrics})
    return [build(name, context) for name in names]
