"""The perimeter a configured setup runs in, read from casebench.yaml (decision 0046)."""

from typing import Any

from casebench import keys, network
from casebench.config import CasebenchConfig
from casebench.corpus.guard import corpus_urls
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.targets.placeholders import VARIABLE, expand_env


def _expanded(url: str) -> str | None:
    """A URL with its `${NAME}`s read; None when one is set nowhere."""
    try:
        return expand_env({"url": url})["url"]
    except KeyError:
        return None


def _models(config: CasebenchConfig) -> list[JudgeConfig]:
    return [*config.judges, *(config.extract.models if config.extract else [])]


def _named_in_headers(headers: Any) -> list[str]:
    if not isinstance(headers, dict):
        return []
    return [name for value in headers.values() for name in VARIABLE.findall(str(value))]


def hosts_of(config: CasebenchConfig) -> list[str]:
    """Every host the config names, and those under `network: allow:`."""
    urls: list[str | None] = []
    target = config.target or {}
    if isinstance(target.get("url"), str):
        urls.append(_expanded(target["url"]))
    for model in _models(config):
        urls.append(getattr(Judge(model).provider, "base_url", None))
    for corpus in config.corpora.values():
        options = {**corpus.options}
        for field in ("base_url", "url"):
            if isinstance(options.get(field), str):
                options[field] = _expanded(options[field])
        urls += corpus_urls(corpus.model_copy(update={"options": options}))
    for route in config.capture.routes if config.capture else []:
        if isinstance(route.get("upstream"), str):
            urls.append(_expanded(route["upstream"]))
    if config.cloud is not None:
        urls.append(_expanded(config.cloud.url))
    named = [network.host_of(url) for url in urls if url]
    return [*named, *(config.network.allow if config.network else [])]


def name_keys(config: CasebenchConfig) -> None:
    """Treat as keys the variables a header or a provider's key names, so nothing a run
    writes or shows holds their values."""
    target = config.target or {}
    names = _named_in_headers(target.get("headers"))
    for corpus in config.corpora.values():
        names += _named_in_headers(corpus.options.get("headers"))
    for model in _models(config):
        named = getattr(Judge(model).provider, "api_key_env", None)
        if named:
            names.append(named)
    if config.cloud is not None:
        names.append(config.cloud.key_env)
    for name in names:
        keys.name(name)


def enforce(config: CasebenchConfig) -> network.Perimeter:
    """From here on, refuse every host the config does not name, and keep its keys out of
    what is written."""
    name_keys(config)
    perimeter = network.Perimeter(hosts_of(config))
    network.enforce(perimeter)
    return perimeter
