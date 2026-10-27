"""`casebench demo`: a bundled project that runs with no key and no data.

Its cases, documents and answers are written for the demo, and its judge's replies are kept
in the run's memo, so scoring asks no model (decision 0061).
"""

from pathlib import Path

import yaml

PROJECT = Path(__file__).parent / "project"
TEMPLATE = Path(__file__).parent / "config.yaml"
CONFIG = "casebench.yaml"


def write_config(project: Path, folder: Path) -> Path:
    """The demo's config in `folder`, reading the corpus in `project`."""
    config = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    config["corpus"]["options"]["path"] = str((project / "corpus").resolve())
    path = folder / CONFIG
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path
