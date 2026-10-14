"""Put cases into a suite folder and freeze it again, so the suite gets a new hash (0039)."""

from pathlib import Path

from casebench.core.case import Case
from casebench.suites.freeze import MANIFEST_FILE, SuiteManifest, freeze, load


def existing(folder: Path) -> tuple[SuiteManifest | None, list[Case]]:
    """The suite in the folder, or none when the folder holds no suite yet."""
    if not (folder / MANIFEST_FILE).is_file():
        return None, []
    return load(folder)


def save(folder: Path, cases: list[Case]) -> tuple[str | None, SuiteManifest]:
    """The hash the suite had, if any, and the manifest it has now. A new suite is named after
    its folder; an existing one keeps its id and how it was generated."""
    before, _ = existing(folder)
    suite_id = before.suite_id if before else folder.name
    generation = before.generation if before else {}
    manifest = freeze(suite_id, cases, folder, generation)
    return (before.content_hash if before else None), manifest


def next_id(suite_id: str, cases: list[Case]) -> str:
    taken = {case.id for case in cases}
    number = len(cases) + 1
    while f"{suite_id}-{number}" in taken:
        number += 1
    return f"{suite_id}-{number}"
