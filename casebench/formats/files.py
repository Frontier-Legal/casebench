"""The committed schema files: one per format version, and the index of those already released."""

import hashlib
import json
from pathlib import Path

from casebench.formats.version import FormatVersion

SCHEMAS = Path(__file__).parent / "schemas"
INDEX = SCHEMAS / "index.json"


def schema_path(version: FormatVersion, root: Path = SCHEMAS) -> Path:
    return root / version.name / version.file_name


def file_hash(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def released() -> dict[str, str]:
    """Each released schema file, by its path under `schemas/`, with the hash it was released
    with. A release adds its new versions here; a listed file never changes again."""
    return json.loads(INDEX.read_text(encoding="utf-8"))["released"]


def is_released(version: FormatVersion) -> bool:
    return f"{version.name}/{version.file_name}" in released()
