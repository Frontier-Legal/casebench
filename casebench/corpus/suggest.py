"""Suggest JSONPath expressions for ids, result descriptions and record fields in a response."""

import re
from collections.abc import Iterator
from typing import Any

from casebench.corpus.mapping import every

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


def results_path(response: Any) -> tuple[str, str] | None:
    """Where each result is, and its id inside one: the list `search_ids` would read."""
    ids = search_ids(response)
    if ids is None:
        return None
    head, _, tail = ids.partition("[*]")
    return f"{head}[*]", f"${tail}"


# English key names a search result commonly uses; a corpus that names them otherwise is mapped
# by hand, and `corpus check` says what is missing (decision 0037).
DESCRIPTION_KEYS = {
    "citation": ("citation", "cite", "reference", "title"),
    "type": ("type", "kind", "category"),
    "passage": ("highlight", "snippet", "passage", "excerpt", "fragment", "match"),
}


def result_fields(response: Any, results: str) -> dict[str, str]:
    """Where the first result most likely keeps its citation, type and matched passage."""
    items = every(results, response)
    if not items or not isinstance(items[0], dict):
        return {}
    item = items[0]
    found: dict[str, str] = {}
    for path, value in _leaves(item):
        if not isinstance(value, str) or _is_id(path):
            continue
        key = _last_key(path.removesuffix("[0]")).casefold()
        for name, words in DESCRIPTION_KEYS.items():
            if name not in found and any(word in key for word in words):
                found[name] = path.removesuffix("[0]")
    return found


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
