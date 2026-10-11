"""Freeze a suite to disk with an id and a content hash, and load it back."""

from collections import Counter
from pathlib import Path

from casebench import __version__
from casebench.core.canonical import canonical_json, content_hash
from casebench.core.case import Case
from casebench.core.model import FrozenRecord

SUITE_FILE = "suite.jsonl"
MANIFEST_FILE = "manifest.json"


class SuiteManifest(FrozenRecord):
    """What a frozen suite is: its id, its hash and the mix of what it holds."""

    suite_id: str
    content_hash: str
    casebench_version: str
    case_count: int
    task_types: dict[str, int]
    reference_sources: dict[str, int]
    approvals: dict[str, int]


class SuiteHashMismatch(ValueError):
    """The cases on disk are not the cases the manifest froze."""


def case_lines(cases: list[Case]) -> list[str]:
    return [canonical_json(case.model_dump(mode="json")) for case in cases]


def manifest_for(suite_id: str, cases: list[Case]) -> SuiteManifest:
    return SuiteManifest(
        suite_id=suite_id,
        content_hash=content_hash(case_lines(cases)),
        casebench_version=__version__,
        case_count=len(cases),
        task_types=dict(Counter(case.task.type for case in cases)),
        reference_sources=dict(Counter(case.reference.source.value for case in cases)),
        approvals=dict(Counter(case.approval.value for case in cases)),
    )


def freeze(suite_id: str, cases: list[Case], folder: Path) -> SuiteManifest:
    """Write `suite.jsonl` and `manifest.json`; the case order is the suite's order."""
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("two cases share an id")
    folder.mkdir(parents=True, exist_ok=True)
    lines = case_lines(cases)
    (folder / SUITE_FILE).write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    manifest = manifest_for(suite_id, cases)
    (folder / MANIFEST_FILE).write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest


def load(folder: Path) -> tuple[SuiteManifest, list[Case]]:
    """Read a frozen suite and refuse it if its cases no longer match the manifest's hash."""
    manifest = SuiteManifest.model_validate_json(
        (folder / MANIFEST_FILE).read_text(encoding="utf-8")
    )
    text = (folder / SUITE_FILE).read_text(encoding="utf-8")
    cases = [Case.model_validate_json(line) for line in text.splitlines() if line]
    found = content_hash(case_lines(cases))
    if found != manifest.content_hash:
        raise SuiteHashMismatch(
            f"suite {manifest.suite_id} was frozen as {manifest.content_hash}, "
            f"but its cases hash to {found}"
        )
    return manifest, cases
