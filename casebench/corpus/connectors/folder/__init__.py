"""The folder connector: one JSON decision record per file."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class Connector:
    """Reads `<path>/*.json`, each file one decision keyed by the decision record's fields."""

    def __init__(self, path: str) -> None:
        self.root = Path(path)
        if not self.root.is_dir():
            raise FileNotFoundError(f"corpus folder {self.root} does not exist")

    def _files(self) -> dict[str, Path]:
        files: dict[str, Path] = {}
        for file in sorted(self.root.glob("*.json")):
            decision_id = json.loads(file.read_text(encoding="utf-8")).get("id", file.stem)
            files[str(decision_id)] = file
        return files

    def list_ids(self) -> Iterable[str]:
        return list(self._files())

    def fetch(self, decision_id: str) -> dict[str, Any]:
        file = self._files().get(decision_id)
        if file is None:
            raise KeyError(f"no decision {decision_id!r} in {self.root}")
        return json.loads(file.read_text(encoding="utf-8"))
