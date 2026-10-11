"""Run a plugin's conformance suite on its own samples and report what it measured."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casebench.adapters import conformance as adapters
from casebench.capture import conformance as capture
from casebench.corpus import conformance as corpus
from casebench.plugins.manifest import (
    SAMPLES_DIR,
    load_object,
    read_manifest,
    registered_entry_point,
)
from casebench.plugins.samples import SuiteResult, options_for
from casebench.providers import conformance as providers

SUITES: dict[str, Callable[[Any, Path], SuiteResult]] = {
    "adapter": adapters.check,
    "connector": corpus.check,
    "parser": capture.check,
    "provider": providers.check,
}


@dataclass
class Report:
    kind: str
    name: str
    problems: list[str] = field(default_factory=list)
    figure_name: str | None = None
    figure: float | None = None
    samples: int = 0

    @property
    def passed(self) -> bool:
        return not self.problems

    def line(self) -> str:
        verdict = "passed" if self.passed else "failed"
        measured = ""
        if self.figure_name and self.figure is not None:
            measured = f", {self.figure_name} {self.figure:.2f} over {self.samples} samples"
        return f"{self.kind} {self.name}: {verdict}{measured}"


def instantiate(implementation: Any, samples: Path) -> Any:
    """Build the plugin with the options in `samples/config.json`, if it has any."""
    if not isinstance(implementation, type):
        return implementation
    return implementation(**options_for(samples))


def run(folder: Path) -> Report:
    manifest = read_manifest(folder)
    kind = manifest.plugin_kind
    report = Report(kind=kind.name, name=manifest.name, figure_name=kind.figure)

    registered = registered_entry_point(folder, manifest)
    if registered is None:
        report.problems.append(
            f"no pyproject.toml registers {manifest.name!r} in the {kind.group} entry points"
        )
    elif registered != manifest.object:
        report.problems.append(
            f"the entry point says {registered} but {folder.name}'s manifest says {manifest.object}"
        )

    samples = folder / SAMPLES_DIR
    try:
        plugin = instantiate(load_object(folder, manifest), samples)
    except Exception as error:
        report.problems.append(f"loading {manifest.object}: {type(error).__name__}: {error}")
        return report
    if not isinstance(plugin, kind.interface):
        report.problems.append(f"{manifest.object} does not meet {kind.interface_path}")
        return report

    suite = SUITES.get(kind.name)
    if suite is None:
        return report
    if not samples.is_dir():
        report.problems.append(f"{folder.name} has no {SAMPLES_DIR}/ folder")
        return report
    result = suite(plugin, samples)
    report.problems.extend(result.problems)
    report.figure, report.samples = result.figure, result.samples
    if result.samples == 0:
        report.problems.append(f"{SAMPLES_DIR}/ holds no samples")
    return report
