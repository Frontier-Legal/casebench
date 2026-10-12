"""The public model catalog, and which installed provider plugin serves an entry (decision 0032)."""

import inspect
import json
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any

import httpx2

from casebench.plugins import registry
from casebench.plugins.kinds import kind_named

CATALOG_URL = "https://models.dev/api.json"


def load(path: Path | None = None) -> dict[str, Any]:
    """A saved copy when given; otherwise fetched for this run and kept in memory only."""
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    response = httpx2.get(CATALOG_URL, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def _catalog_values(provider: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_url": provider.get("api"),
        "api_key_env": (provider.get("env") or [None])[0],
        "family": model.get("family") or provider.get("id"),
        "max_tokens": (model.get("limit") or {}).get("output") or None,
    }


@dataclass(frozen=True)
class Serving:
    """A plugin that speaks an entry's API, the options it got, and those the user must give."""

    plugin: str
    options: dict[str, Any]
    missing: list[str] = field(default_factory=list)
    packages: tuple[str, ...] = ()


def offer(plugin_name: str, provider: dict[str, Any], model: dict[str, Any]) -> Serving:
    """Every catalog value the plugin's constructor takes. An output cap is set only where the
    plugin requires one. A base URL the catalog lacks is asked for unless the plugin speaks
    this entry's API, whose default it knows."""
    kind = kind_named("provider")
    plugin = registry.load(kind, plugin_name)
    parameters = inspect.signature(plugin).parameters
    values = _catalog_values(provider, model)
    options = {}
    for name, value in values.items():
        if name not in parameters or value is None:
            continue
        if name == "max_tokens" and parameters[name].default is not inspect.Parameter.empty:
            continue
        options[name] = value
    native = provider.get("npm") in getattr(plugin, "speaks", ())
    missing = [] if native or "base_url" not in parameters or values["base_url"] else ["base_url"]
    return Serving(plugin_name, options, missing, tuple(getattr(plugin, "packages", ())))


def speakers(provider: dict[str, Any]) -> list[str]:
    """The installed plugins that name this entry's API as theirs."""
    kind = kind_named("provider")
    return [
        item.name
        for item in registry.available(kind)
        if provider.get("npm") in getattr(registry.load(kind, item.name, item.source), "speaks", ())
    ]


def plugins() -> list[str]:
    return sorted({item.name for item in registry.available(kind_named("provider"))})


def installed(package: str) -> bool:
    try:
        distribution(package)
    except PackageNotFoundError:
        return False
    return True
