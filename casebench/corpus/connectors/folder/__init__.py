"""The folder connector: one JSON document record per file."""

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

WORD = re.compile(r"\w+")


def _words(text: str) -> set[str]:
    return set(WORD.findall(text.casefold()))


class Connector:
    """Reads `<path>/*.json`, each file one document keyed by the decision record's fields.

    Search counts how many of the query's words a document contains, which is enough to
    resolve a citation in a small folder; a large store belongs behind a real search API.
    """

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
            raise KeyError(f"no document {decision_id!r} in {self.root}")
        return json.loads(file.read_text(encoding="utf-8"))

    def search(self, text: str, limit: int) -> list[str]:
        wanted = _words(text)
        scored = []
        for decision_id, file in self._files().items():
            record = json.loads(file.read_text(encoding="utf-8"))
            found = _words(" ".join(str(v) for v in record.values() if isinstance(v, str)))
            overlap = len(wanted & found)
            if overlap:
                scored.append((-overlap, decision_id))
        return [decision_id for _, decision_id in sorted(scored)[:limit]]
