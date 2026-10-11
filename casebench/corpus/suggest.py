"""Suggest JSONPath expressions for ids and decision-record fields from one live response."""

import re
from collections.abc import Iterator
from typing import Any

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _leaves(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaves(item, f"{path}.{key}")
    elif isinstance(value, list) and value:
        yield from _leaves(value[0], f"{path}[0]")
    else:
        yield path, value


def _last_key(path: str) -> str:
    return re.split(r"[.\[]", path)[-1].rstrip("]")


def _is_id(path: str) -> bool:
    """`id`, `uuid`, `work_id` or `workId`; not `valid` or `paid`."""
    key = _last_key(path)
    return key.casefold() in ("id", "uuid") or key.casefold().endswith("_id") or key.endswith("Id")


def search_ids(response: Any) -> str | None:
    """The first id-like field inside the first list of objects, as a path over every item."""
    for path, value in _leaves(response):
        if "[0]" in path and _is_id(path) and isinstance(value, str | int):
            head, _, tail = path.partition("[0]")
            return f"{head}[*]{tail}"
    return None


def document_fields(document: Any) -> dict[str, str]:
    """Where a fetched document most likely keeps its id, text, court, date and jurisdiction."""
    leaves = list(_leaves(document))
    strings = [(p, v) for p, v in leaves if isinstance(v, str)]
    found: dict[str, str] = {}
    ids = [p for p, v in leaves if _is_id(p) and "[0]" not in p and isinstance(v, str | int)]
    if ids:
        found["id"] = ids[0]
    if strings:
        found["text"] = max(strings, key=lambda leaf: len(leaf[1]))[0]
    for path, value in strings:
        key = _last_key(path).casefold()
        if "date" not in found and ISO_DATE.match(value):
            found["date"] = path
        if "court" not in found and any(w in path.casefold() for w in ("court", "issuer")):
            found["court"] = path
        if "jurisdiction" not in found and ("jurisdiction" in path.casefold() or key == "country"):
            found["jurisdiction"] = path
    return found
