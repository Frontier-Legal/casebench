"""The http connector: any document API, described by paths and JSONPath expressions."""

from typing import Any

import httpx2
from pydantic import Field, model_validator

from casebench.core.model import Record
from casebench.corpus.interface import ListingNotSupported
from casebench.corpus.mapping import every, record_fields
from casebench.corpus.results import SearchResult, results_of
from casebench.targets.placeholders import expand_env


class HttpCorpusConfig(Record):
    """Paths are relative to `base_url`; `{id}`, `{text}` and `{limit}` are filled per call.
    `search_results` finds each result in a search response, and `result_fields` reads its
    `id`, `citation`, `type` and `passage` inside it (decision 0037); without them,
    `search_ids` finds the ids alone."""

    base_url: str
    headers: dict[str, str] = Field(default_factory=dict)
    fetch_path: str
    search_path: str
    search_params: dict[str, str] = Field(default_factory=lambda: {"q": "{text}"})
    search_ids: str = "$"
    search_results: str | None = None
    result_fields: dict[str, str] = Field(default_factory=dict)
    fields: dict[str, str] = Field(default_factory=dict)
    list_path: str | None = None
    list_ids: str | None = None
    timeout_s: float | None = None

    @model_validator(mode="after")
    def _results_have_ids(self) -> "HttpCorpusConfig":
        if self.search_results and "id" not in self.result_fields:
            raise ValueError("result_fields needs an id when search_results is set")
        return self


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

    def search_raw(self, text: str, limit: int, filters: dict[str, Any] | None = None) -> Any:
        """`filters` are further query parameters, such as a document type (decision 0037)."""
        params = {
            key: value.replace("{text}", text).replace("{limit}", str(limit))
            for key, value in self.config.search_params.items()
        }
        params |= {key: str(value) for key, value in (filters or {}).items()}
        return self._get(self.config.search_path, params)

    def fetch(self, decision_id: str) -> dict[str, Any]:
        return record_fields(self.fetch_raw(decision_id), self.config.fields)

    def search_results(
        self, text: str, limit: int, filters: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        config = self.config
        response = self.search_raw(text, limit, filters)
        found = results_of(response, config.search_results, config.result_fields, config.search_ids)
        return found[:limit]

    def search(self, text: str, limit: int) -> list[str]:
        return [result.id for result in self.search_results(text, limit)]

    def list_ids(self) -> list[str]:
        if not self.config.list_path or not self.config.list_ids:
            raise ListingNotSupported("this API has no listing configured")
        return [str(item) for item in every(self.config.list_ids, self._get(self.config.list_path))]
