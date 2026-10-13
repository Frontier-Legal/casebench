"""Keep fetched documents, and a metered store's searches, on disk: each costs one call ever."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from casebench.corpus.interface import list_ids

DEFAULT_CACHE = Path(".casebench") / "corpus-cache"
SEARCHES = "searches"


def corpus_key(connector: str, options: dict[str, Any]) -> str:
    """One folder per connector and its options, so two stores never share a cache."""
    settings = json.dumps({"connector": connector, "options": options}, sort_keys=True)
    return f"{connector}-{hashlib.sha256(settings.encode()).hexdigest()}"


class CachedConnector:
    """Wraps any connector: fetches go to disk first, and so do searches when the store
    charges for them (decision 0033); listings pass through. A free store is searched afresh,
    so documents added to it are found."""

    def __init__(self, connector: Any, folder: Path, keep_searches: bool = False) -> None:
        self.connector = connector
        self.folder = folder
        self.keep_searches = keep_searches
        self.fetched = 0
        self.searched = 0

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

    def _search_path(self, text: str, limit: int) -> Path:
        asked = json.dumps([text, limit], ensure_ascii=False)
        return self.folder / SEARCHES / f"{hashlib.sha256(asked.encode()).hexdigest()}.json"

    def search_cached(self, text: str, limit: int) -> bool:
        return self.keep_searches and self._search_path(text, limit).is_file()

    def search(self, text: str, limit: int) -> list[str]:
        """The same query, asked again of a metered store, is answered from disk."""
        path = self._search_path(text, limit)
        if self.keep_searches and path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        found = self.connector.search(text, limit)
        self.searched += 1
        if self.keep_searches:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(found, ensure_ascii=False), encoding="utf-8")
        return found

    def list_ids(self) -> list[str]:
        return list(list_ids(self.connector))


def cached_documents(connector: str, options: dict[str, Any], root: Path = DEFAULT_CACHE) -> int:
    """How many of one store's documents are on disk already."""
    return sum(1 for _ in (root / corpus_key(connector, options)).glob("*.json"))


def cached_searches(connector: str, options: dict[str, Any], root: Path = DEFAULT_CACHE) -> int:
    """How many of one store's searches are on disk already."""
    return sum(1 for _ in (root / corpus_key(connector, options) / SEARCHES).glob("*.json"))


def clear(root: Path = DEFAULT_CACHE) -> tuple[int, int]:
    """Delete every cached document and search; returns how many of each there were."""
    if not root.is_dir():
        return 0, 0
    documents = sum(1 for _ in root.glob("*/*.json"))
    searches = sum(1 for _ in root.glob(f"*/{SEARCHES}/*.json"))
    shutil.rmtree(root)
    return documents, searches
