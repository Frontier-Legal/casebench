"""Suggest where a response keeps a field from its shape and values alone, never from key names."""

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


def leaves(value: Any) -> list[tuple[str, Any]]:
    """Every scalar in a response, by JSONPath, with its value: what a user picks a field from.
    A list is shown by its first item; a list of strings, such as highlights, by itself."""
    found = []
    for path, item in _leaves(value):
        if path.endswith("[0]") and isinstance(item, str):
            found.append((path.removesuffix("[0]"), item))
        elif isinstance(item, str | int | float):
            found.append((path, item))
    return found


def _first_list(value: Any, path: str = "$") -> tuple[str, list[Any]] | None:
    if isinstance(value, list):
        return path, value
    if isinstance(value, dict):
        for key, item in value.items():
            if (found := _first_list(item, f"{path}.{key}")) is not None:
                return found
    return None


def results_path(response: Any) -> str | None:
    """The first list of objects in a search response, as a path over each of them."""
    found = _first_list(response)
    if found is None or not found[1] or not isinstance(found[1][0], dict):
        return None
    return f"{found[0]}[*]"


def search_ids(response: Any) -> str | None:
    """The first list in a search response, when it holds the ids themselves."""
    found = _first_list(response)
    if found is None or not found[1] or not isinstance(found[1][0], str | int):
        return None
    return f"{found[0]}[*]"


def first_result(response: Any, results: str) -> dict[str, Any] | None:
    found = _first_list(response)
    if found is None or f"{found[0]}[*]" != results or not found[1]:
        return None
    return found[1][0] if isinstance(found[1][0], dict) else None


def document_fields(document: Any, fetched_id: str) -> dict[str, str]:
    """From the document's values alone: the field holding the id it was fetched by, the
    longest text, and the first value shaped like a date. Court and jurisdiction are left to
    the user, since nothing in a value says which it is (decision 0043)."""
    found_leaves = list(_leaves(document))
    strings = [(p, v) for p, v in found_leaves if isinstance(v, str)]
    found: dict[str, str] = {}
    ids = [p for p, v in found_leaves if "[0]" not in p and str(v) == fetched_id]
    if ids:
        found["id"] = ids[0]
    if strings:
        found["text"] = max(strings, key=lambda leaf: len(leaf[1]))[0]
    dates = [p for p, v in strings if ISO_DATE.match(v)]
    if dates:
        found["date"] = dates[0]
    return found
