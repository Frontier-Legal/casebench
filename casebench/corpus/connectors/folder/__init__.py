"""The folder connector: one JSON document record per file."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from casebench.corpus.passage import best_passage, words
from casebench.corpus.results import SearchResult


def _matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    """A filter names a field the document must equal, at its top level or in its metadata."""
    metadata = record.get("metadata") or {}
    return all(record.get(k, metadata.get(k)) == value for k, value in filters.items())


class Connector:
    """Reads `<path>/*.json`, each file one document keyed by the decision record's fields.

    Search counts how many of the query's words a document contains, which is enough to
    resolve a citation in a small folder; a large store belongs behind a real search API. A
    result is described by its file's name and the paragraph the search matched (decision
    0037).
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

    def search_results(
        self, text: str, limit: int, filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        wanted = words(text)
        scored = []
        for decision_id, file in self._files().items():
            record = json.loads(file.read_text(encoding="utf-8"))
            if not _matches(record, filters or {}):
                continue
            found = words(" ".join(str(v) for v in record.values() if isinstance(v, str)))
            overlap = len(wanted & found)
            if overlap:
                passage = best_passage(str(record.get("text", "")), text)
                scored.append((-overlap, decision_id, file.name, passage))
        return [
            SearchResult(id=decision_id, citation=name, passage=passage)
            for _, decision_id, name, passage in sorted(scored)[:limit]
        ]

    def search(self, text: str, limit: int) -> list[str]:
        return [result.id for result in self.search_results(text, limit)]
