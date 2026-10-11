"""Keep every fetched document on disk, so a document costs one call ever."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from casebench.corpus.interface import list_ids

DEFAULT_CACHE = Path(".casebench") / "corpus-cache"


def corpus_key(connector: str, options: dict[str, Any]) -> str:
    """One folder per connector and its options, so two stores never share a cache."""
    settings = json.dumps({"connector": connector, "options": options}, sort_keys=True)
    return f"{connector}-{hashlib.sha256(settings.encode()).hexdigest()}"


class CachedConnector:
    """Wraps any connector: fetches go to disk first; searches and listings pass through."""

    def __init__(self, connector: Any, folder: Path) -> None:
        self.connector = connector
        self.folder = folder
        self.fetched = 0

    def _path(self, decision_id: str) -> Path:
        return self.folder / f"{hashlib.sha256(decision_id.encode()).hexdigest()}.json"

    def cached(self, decision_id: str) -> bool:
        return self._path(decision_id).is_file()

    def fetch(self, decision_id: str) -> dict[str, Any]:
        path = self._path(decision_id)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        document = self.connector.fetch(decision_id)
        self.fetched += 1
        self.folder.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return document

    def search(self, text: str, limit: int) -> list[str]:
        return self.connector.search(text, limit)

    def list_ids(self) -> list[str]:
        return list(list_ids(self.connector))


def cached_documents(connector: str, options: dict[str, Any], root: Path = DEFAULT_CACHE) -> int:
    """How many of one store's documents are on disk already."""
    return sum(1 for _ in (root / corpus_key(connector, options)).glob("*.json"))


def clear(root: Path = DEFAULT_CACHE) -> int:
    """Delete every cached document; returns how many there were."""
    if not root.is_dir():
        return 0
    count = sum(1 for _ in root.glob("*/*.json"))
    shutil.rmtree(root)
    return count
