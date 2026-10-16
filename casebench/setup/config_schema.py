"""The JSON Schema an editor checks `casebench.yaml` against, from the installed version.

Init writes it under `.casebench/` and names it on the config's first line, so the schema is
always the one the installed Casebench reads (decision 0061).
"""

import json
from pathlib import Path
from typing import Any

from casebench.config import CasebenchConfig
from casebench.formats.schema import schema_of

SCHEMA_FILE = Path(".casebench") / "casebench.schema.json"
LINE = f"# yaml-language-server: $schema={SCHEMA_FILE.as_posix()}\n"


def config_schema() -> dict[str, Any]:
    """The config model's schema, with `corpus:` and `judge:`, the forms for one of each."""
    schema = schema_of(CasebenchConfig)
    properties = schema["properties"]
    properties["corpus"] = {"$ref": "#/$defs/CorpusConfig"}
    properties["judge"] = {"$ref": "#/$defs/JudgeConfig"}
    return schema


def write_schema(folder: Path) -> Path:
    path = folder / SCHEMA_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config_schema(), ensure_ascii=False, indent=2) + "\n", "utf-8")
    return path
