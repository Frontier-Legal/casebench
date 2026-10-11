"""Read a document's decision-record fields and a search result's ids by JSONPath."""

from typing import Any

from jsonpath_ng.ext.parser import parse as jsonpath


def first(expression: str, document: Any) -> Any | None:
    matches = jsonpath(expression).find(document)
    return matches[0].value if matches else None


def every(expression: str, document: Any) -> list[Any]:
    return [match.value for match in jsonpath(expression).find(document)]


def record_fields(document: Any, fields: dict[str, str]) -> dict[str, Any]:
    """Only the fields the expressions find; a missing one is left out, so it is reported."""
    found: dict[str, Any] = {}
    for name, expression in fields.items():
        value = first(expression, document)
        if value not in (None, ""):
            found[name] = str(value) if name == "id" else value
    return found
