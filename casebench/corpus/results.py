"""A search result as the corpus describes it: its id, citation, type and matched passage."""

from typing import Any

from casebench.core.model import FrozenRecord
from casebench.corpus.mapping import every, first

# What a corpus may say about a result, besides its id (decision 0037).
DESCRIBED = ("citation", "type", "passage")


class SearchResult(FrozenRecord):
    """`citation` is how the corpus cites the document, `type` what kind of document it is, and
    `passage` the part of it the search matched; each is None when the corpus does not say."""

    id: str
    citation: str | None = None
    type: str | None = None
    passage: str | None = None

    @property
    def described(self) -> bool:
        return any(getattr(self, name) is not None for name in DESCRIBED)


def _text(value: Any) -> str | None:
    """A passage given as several highlights is read as one, a line each."""
    if isinstance(value, list):
        value = "\n".join(str(item) for item in value if item not in (None, ""))
    return None if value in (None, "") else str(value)


def read_results(response: Any, results: str, fields: dict[str, str]) -> list[SearchResult]:
    """Each result `results` finds, read by `fields` relative to it; one with no id is skipped."""
    found = []
    for item in every(results, response):
        result_id = first(fields["id"], item)
        if result_id in (None, ""):
            continue
        described = {name: _text(first(fields[name], item)) for name in DESCRIBED if name in fields}
        found.append(SearchResult(id=str(result_id), **described))
    return found


def results_of(
    response: Any, results: str | None, fields: dict[str, str], ids: str
) -> list[SearchResult]:
    """Described results where a connector maps them, else the ids `ids` finds."""
    if results:
        return read_results(response, results, fields)
    return [SearchResult(id=str(found)) for found in every(ids, response)]


def as_result(entry: Any) -> SearchResult:
    """A kept search lists ids, or results with their description."""
    return SearchResult(id=entry) if isinstance(entry, str) else SearchResult.model_validate(entry)
