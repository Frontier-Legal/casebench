"""Capture routes for the corpora the config names, so an agent's own searches are recorded.

An agent that searches the same document store Casebench checks citations against calls it
at the corpus's address. A Python agent's calls arrive at the proxy by where they go
(decision 0044), so a route at that host reads them: a search as a retrieval with the ids
the corpus's search results hold, a fetch as the document its path names.
"""

from typing import Any
from urllib.parse import urlsplit

from casebench.capture.proxy.routes import Route
from casebench.corpus.binding import CorpusConfig
from casebench.targets.placeholders import expand_env


def ids_path(options: dict[str, Any]) -> str | None:
    """Where a corpus's search response holds its ids, as one JSONPath."""
    results, fields = options.get("search_results"), options.get("result_fields") or {}
    if results and fields.get("id"):
        return f"{results}{str(fields['id']).removeprefix('$')}"
    return options.get("search_ids")


def corpus_routes(corpora: dict[str, CorpusConfig], taken: list[Route]) -> list[Route]:
    """A route at each HTTP corpus's host that no route covers yet. A base URL that names a
    variable is read as the corpus reads it; one that cannot be read here gets no route."""
    covered = {urlsplit(route.upstream).netloc for route in taken}
    made = []
    for name, corpus in corpora.items():
        if corpus.connector != "http" or not corpus.options.get("base_url"):
            continue
        try:
            base = expand_env({"base_url": str(corpus.options["base_url"])})["base_url"]
        except KeyError:
            continue
        parts = urlsplit(base)
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.netloc in covered:
            continue
        covered.add(parts.netloc)
        made.append(
            Route(
                name=f"corpus-{name}",
                upstream=f"{parts.scheme}://{parts.netloc}",
                step="retrieval",
                doc_ids=ids_path(corpus.options),
                fetch_path=corpus.options.get("fetch_path"),
            )
        )
    return made
