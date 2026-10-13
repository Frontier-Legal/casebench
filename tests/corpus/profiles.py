"""Profile files for the tests, pointing at the test document API or MCP server."""

from pathlib import Path
from typing import Any

import yaml

FIELDS = {
    "id": "$.work_id",
    "jurisdiction": "$.jurisdiction.code",
    "court": "$.issuers[0].name",
    "date": "$.dates[1].date",
    "text": "$.expressions[0].text",
}


def profile(
    folder: Path,
    connector: str,
    options: dict[str, Any],
    file_name: str = "provider.yaml",
    **extra: Any,
) -> Path:
    path = folder / file_name
    data = {
        "format": "casebench.profile/1.0",
        "name": "Test Provider",
        "jurisdictions": ["TR"],
        "terms": "https://example.com/terms",
        "key_env": "DOC_KEY",
        "metered": "search",
        "connector": connector,
        "options": options,
        "probe": "feshi",
        **extra,
    }
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def http_options(base: str, fields: dict[str, str] = FIELDS) -> dict[str, Any]:
    return {
        "base_url": base,
        "headers": {"Authorization": "Bearer ${DOC_KEY}"},
        "search_path": "/search",
        "search_params": {"q": "{text}"},
        "search_ids": "$.results[*].work.work_id",
        "fetch_path": "/documents/{id}",
        "fields": fields,
    }
