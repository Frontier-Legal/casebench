"""Refuse a config whose corpus is the system under test (decision 0025)."""

from typing import Any
from urllib.parse import urlsplit

from casebench.corpus.binding import CorpusConfig


class SelfCheckRefused(ValueError):
    pass


def _normal(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc.lower()}{parts.path.rstrip('/')}"


def corpus_urls(corpus: CorpusConfig) -> list[str]:
    options = corpus.options
    base = options.get("base_url")
    urls = [u for u in (base, options.get("url")) if isinstance(u, str)]
    if isinstance(base, str):
        for key in ("search_path", "fetch_path"):
            path = options.get(key)
            if isinstance(path, str):
                urls.append(base.rstrip("/") + path.split("{")[0])
    return [_normal(url) for url in urls]


def refuse_self_check(target: dict[str, Any], corpus: CorpusConfig | None) -> None:
    url = target.get("url")
    if corpus is None or not isinstance(url, str):
        return
    if _normal(url) in corpus_urls(corpus):
        raise SelfCheckRefused(
            f"the corpus points at the target's own endpoint ({url}); citation checks must "
            "read raw decisions, never ask the system under test. Point the corpus at the "
            "document store itself."
        )
