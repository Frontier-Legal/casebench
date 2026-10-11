"""Read casebench.yaml."""

from pathlib import Path
from typing import Any

import yaml

from casebench.capture.config import CaptureConfig
from casebench.core.model import Record
from casebench.corpus.binding import CorpusConfig

DEFAULT_CONFIG = Path("casebench.yaml")


class CasebenchConfig(Record):
    target: dict[str, Any]
    corpus: CorpusConfig | None = None
    capture: CaptureConfig | None = None


def load_config(path: Path = DEFAULT_CONFIG) -> CasebenchConfig:
    """`yaml.safe_load` only: a config never constructs Python objects."""
    if not path.is_file():
        raise FileNotFoundError(f"{path} does not exist; run casebench init or pass --config")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return CasebenchConfig.model_validate(data)
