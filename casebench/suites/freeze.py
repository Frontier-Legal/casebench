"""Freeze a suite to disk with an id and a content hash, and load it back."""

import json
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import Field

from casebench import __version__
from casebench.core.canonical import canonical_json, content_hash
from casebench.core.case import FORMAT as CASE_FORMAT
from casebench.core.case import Case
from casebench.core.model import FrozenRecord
from casebench.formats.extensions import Extensions
from casebench.formats.read import ignored_note, read
from casebench.formats.version import FormatVersion, UnreadableFormat

SUITE_FILE = "suite.jsonl"
MANIFEST_FILE = "manifest.json"
FORMAT = FormatVersion("suite", 1, 0)


class SuiteManifest(FrozenRecord):
    """What a frozen suite is: its format, its id, its hash and the mix of what it holds.
    `case_format` is the format of every line of `suite.jsonl`."""

    format: str = Field(pattern=FORMAT.pattern)
    case_format: str = Field(pattern=CASE_FORMAT.pattern)
    suite_id: str
    content_hash: str
    casebench_version: str
    case_count: int
    task_types: dict[str, int]
    reference_sources: dict[str, int]
    approvals: dict[str, int]
    generation: dict[str, Any] = Field(default_factory=dict)
    extensions: Extensions = Field(default_factory=dict)


class SuiteHashMismatch(ValueError):
    """The cases on disk are not the cases the manifest froze."""


def case_lines(cases: list[Case]) -> list[str]:
    return [canonical_json(case.model_dump(mode="json")) for case in cases]


def manifest_for(
    suite_id: str, cases: list[Case], generation: dict[str, Any] | None = None
) -> SuiteManifest:
    return SuiteManifest(
        format=str(FORMAT),
        case_format=str(CASE_FORMAT),
        suite_id=suite_id,
        content_hash=content_hash(case_lines(cases)),
        casebench_version=__version__,
        case_count=len(cases),
        task_types=dict(Counter(case.task.type for case in cases)),
        reference_sources=dict(Counter(case.reference.source.value for case in cases)),
        approvals=dict(Counter(case.approval.value for case in cases)),
        generation=generation or {},
    )


def freeze(
    suite_id: str, cases: list[Case], folder: Path, generation: dict[str, Any] | None = None
) -> SuiteManifest:
    """Write `suite.jsonl` and `manifest.json`; the case order is the suite's order."""
    ids = [case.id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("two cases share an id")
    folder.mkdir(parents=True, exist_ok=True)
    lines = case_lines(cases)
    (folder / SUITE_FILE).write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    manifest = manifest_for(suite_id, cases, generation)
    (folder / MANIFEST_FILE).write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return manifest


def _declared(raw: dict[str, Any], path: Path) -> FormatVersion:
    if "format" not in raw:
        raise UnreadableFormat(f"{path} names no format; freeze the suite again")
    return FormatVersion.parse(raw["format"])


def load(folder: Path) -> tuple[SuiteManifest, list[Case]]:
    """Read a frozen suite at the formats its manifest names, and refuse it if its cases no
    longer match the manifest's hash. The hash is taken over the lines as written, so a suite
    at a newer minor version keeps its hash when its unknown fields are ignored."""
    path = folder / MANIFEST_FILE
    raw = json.loads(path.read_text(encoding="utf-8"))
    declared = _declared(raw, path)
    manifest, ignored = read(SuiteManifest, raw, declared, FORMAT)
    if ignored:
        warnings.warn(ignored_note(str(path), declared, FORMAT, ignored), stacklevel=2)
    case_format = FormatVersion.parse(manifest.case_format)
    text = (folder / SUITE_FILE).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.splitlines() if line]
    cases: list[Case] = []
    skipped: list[str] = []
    for row in rows:
        case, ignored = read(Case, row, case_format, CASE_FORMAT)
        cases.append(case)
        skipped += ignored
    if skipped:
        where = str(folder / SUITE_FILE)
        warnings.warn(ignored_note(where, case_format, CASE_FORMAT, skipped), stacklevel=2)
    found = content_hash(canonical_json(row) for row in rows)
    if found != manifest.content_hash:
        raise SuiteHashMismatch(
            f"suite {manifest.suite_id} was frozen as {manifest.content_hash}, "
            f"but its cases hash to {found}"
        )
    return manifest, cases
