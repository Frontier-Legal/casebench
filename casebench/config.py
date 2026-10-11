"""Read casebench.yaml."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError, model_validator

from casebench.capture.config import CaptureConfig
from casebench.core.model import Record
from casebench.corpus.binding import CorpusConfig
from casebench.corpus.guard import refuse_self_check

DEFAULT_CONFIG = Path("casebench.yaml")


class ConfigError(ValueError):
    """casebench.yaml is missing or does not validate; the message says where."""


class CasebenchConfig(Record):
    target: dict[str, Any] | None = None
    corpus: CorpusConfig | None = None
    capture: CaptureConfig | None = None

    @model_validator(mode="after")
    def _corpus_is_not_the_target(self) -> "CasebenchConfig":
        refuse_self_check(self.target or {}, self.corpus)
        return self


def relative_to(base: Path, entry: str) -> str:
    """A `script.py[:function]` entry with a relative path, made relative to the config's
    folder; module entries and absolute paths stay as they are."""
    location, colon, function = entry.rpartition(":")
    if not location or not location.endswith(".py"):
        location, colon, function = entry, "", ""
    if not location.endswith(".py") or Path(location).is_absolute():
        return entry
    return f"{(base / location).resolve()}{colon}{function}"


def load_config(path: Path = DEFAULT_CONFIG) -> CasebenchConfig:
    """`yaml.safe_load` only: a config never constructs Python objects. Script paths in it
    are relative to the config file."""
    if not path.is_file():
        raise ConfigError(f"{path} does not exist; run casebench init or pass --config")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base = path.resolve().parent
    target = data.get("target") or {}
    if isinstance(target.get("entry"), str):
        target["entry"] = relative_to(base, target["entry"])
    for function in (data.get("capture") or {}).get("functions") or []:
        if isinstance(function, dict) and isinstance(function.get("function"), str):
            function["function"] = relative_to(base, function["function"])
    try:
        return CasebenchConfig.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(
            ".".join(str(part) for part in e["loc"]) + ": " + e["msg"].removeprefix("Value error, ")
            if e["loc"]
            else e["msg"].removeprefix("Value error, ")
            for e in error.errors()
        )
        raise ConfigError(f"{path}: {problems}") from error


def target_of(config: CasebenchConfig) -> dict[str, Any]:
    """The target a command needs; a config with none says how to add one."""
    if config.target is None:
        raise ConfigError("the config has no target; add `target:` to casebench.yaml")
    return config.target
