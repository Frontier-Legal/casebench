"""The http connector: any document API, described by paths and JSONPath expressions."""

from typing import Any

import httpx2
from pydantic import Field

from casebench.core.model import Record
from casebench.corpus.interface import ListingNotSupported
from casebench.corpus.mapping import every, record_fields
from casebench.targets.placeholders import expand_env


class HttpCorpusConfig(Record):
    """Paths are relative to `base_url`; `{id}`, `{text}` and `{limit}` are filled per call."""

    base_url: str
    headers: dict[str, str] = Field(default_factory=dict)
    fetch_path: str
    search_path: str
    search_params: dict[str, str] = Field(default_factory=lambda: {"q": "{text}"})
    search_ids: str = "$"
    fields: dict[str, str] = Field(default_factory=dict)
    list_path: str | None = None
    list_ids: str | None = None
    timeout_s: float | None = None


class Connector:
    def __init__(self, **options: Any) -> None:
        self.config = HttpCorpusConfig.model_validate(options)
        self.client = httpx2.Client(
            base_url=self.config.base_url.rstrip("/"),
            headers=expand_env(self.config.headers),
            timeout=self.config.timeout_s,
        )

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_raw(self, decision_id: str) -> Any:
        return self._get(self.config.fetch_path.replace("{id}", decision_id))

    def search_raw(self, text: str, limit: int) -> Any:
        params = {
            key: value.replace("{text}", text).replace("{limit}", str(limit))
            for key, value in self.config.search_params.items()
        }
        return self._get(self.config.search_path, params)

    def fetch(self, decision_id: str) -> dict[str, Any]:
        return record_fields(self.fetch_raw(decision_id), self.config.fields)

    def search(self, text: str, limit: int) -> list[str]:
        found = every(self.config.search_ids, self.search_raw(text, limit))
        return [str(item) for item in found][:limit]

    def list_ids(self) -> list[str]:
        if not self.config.list_path or not self.config.list_ids:
            raise ListingNotSupported("this API has no listing configured")
        return [str(item) for item in every(self.config.list_ids, self._get(self.config.list_path))]
