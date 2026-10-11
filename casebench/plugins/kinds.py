"""Every plugin kind: its entry-point group, its interface and where built-ins live."""

from dataclasses import dataclass

from casebench.adapters.interface import JurisdictionAdapter
from casebench.capture.interface import CaptureParser
from casebench.corpus.interface import CorpusConnector
from casebench.exporters.interface import Exporter
from casebench.metrics.base import Metric
from casebench.providers.interface import ModelProvider
from casebench.references.interface import ReferenceBuilder
from casebench.targets.interface import Target
from casebench.tasks.interface import TaskType


@dataclass(frozen=True)
class PluginKind:
    name: str
    group: str
    interface: type
    built_in_root: str
    figure: str | None = None

    @property
    def interface_path(self) -> str:
        return f"{self.interface.__module__}.{self.interface.__qualname__}"

    @property
    def conformance_command(self) -> str:
        return "casebench plugin test <path>"


KINDS: tuple[PluginKind, ...] = (
    PluginKind(
        "adapter",
        "casebench.adapters",
        JurisdictionAdapter,
        "casebench/jurisdictions",
        "extraction accuracy",
    ),
    PluginKind(
        "connector",
        "casebench.corpus",
        CorpusConnector,
        "casebench/corpus/connectors",
        "fields covered",
    ),
    PluginKind(
        "parser", "casebench.capture", CaptureParser, "casebench/capture/parsers", "calls parsed"
    ),
    PluginKind(
        "provider",
        "casebench.providers",
        ModelProvider,
        "casebench/providers/builtin",
        "responses parsed",
    ),
    PluginKind("task", "casebench.tasks", TaskType, "casebench/tasks/builtin"),
    PluginKind(
        "reference", "casebench.references", ReferenceBuilder, "casebench/references/builtin"
    ),
    PluginKind("target", "casebench.targets", Target, "casebench/targets/builtin"),
    PluginKind("metric", "casebench.metrics", Metric, "casebench/metrics/builtin"),
    PluginKind("exporter", "casebench.exporters", Exporter, "casebench/exporters/builtin"),
)

BY_NAME = {kind.name: kind for kind in KINDS}


def kind_named(name: str) -> PluginKind:
    try:
        return BY_NAME[name]
    except KeyError:
        known = ", ".join(BY_NAME)
        raise ValueError(f"no plugin kind {name!r}; the kinds are {known}") from None
