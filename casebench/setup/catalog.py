"""The public model catalog, and which installed provider plugin serves an entry (decision 0032)."""

import inspect
import json
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any

from casebench import network
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named

CATALOG_URL = "https://models.dev/api.json"


def load(path: Path | None = None) -> dict[str, Any]:
    """A saved copy when given; otherwise fetched for this run and kept in memory only. A
    redirect is followed within the catalog's own host only (decision 0046)."""
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    with network.client(follow_redirects=True) as client:
        response = client.get(CATALOG_URL)
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


def model_block(plugin: str, model: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """The config block for a catalog model served by a plugin, with the options it takes."""
    block: dict[str, Any] = {"provider": plugin, "model": model["id"], "options": options}
    # A matching call is split only when it would not fit this window (decision 0037).
    window = (model.get("limit") or {}).get("context")
    if window:
        block["context_window"] = window
    # So a run can say what it cost; without a price it counts tokens only (decision 0038).
    cost = model.get("cost") or {}
    if cost.get("input") is not None and cost.get("output") is not None:
        block["price"] = {"input": cost["input"], "output": cost["output"]}
    return block


def speakers(provider: dict[str, Any]) -> list[str]:
    """The installed plugins that name this entry's API as theirs."""
    kind = kind_named("provider")
    return [
        item.name
        for item in registry.available(kind)
        if provider.get("npm") in getattr(registry.load(kind, item.name, item.source), "speaks", ())
    ]


def entry_for(catalog: dict[str, Any], model_id: str) -> dict[str, Any] | None:
    """The catalog's entry for a model id, matched by the id or its last path segment."""
    short = model_id.rsplit("/", 1)[-1]
    for provider in catalog.values():
        for found_id, model in (provider.get("models") or {}).items():
            if found_id in (model_id, short) or found_id.rsplit("/", 1)[-1] == short:
                return model
    return None


def families(catalog: dict[str, Any], names: list[str]) -> dict[str, str]:
    """The family of each model id the catalog knows, by its id or its last path segment, so
    `accounts/x/models/name` is found as `name`."""
    known: dict[str, str] = {}
    for provider_id, provider in catalog.items():
        for model_id, model in (provider.get("models") or {}).items():
            family = model.get("family") or provider_id
            known.setdefault(model_id, family)
            known.setdefault(model_id.rsplit("/", 1)[-1], family)
    found = {}
    for name in names:
        family = known.get(name) or known.get(name.rsplit("/", 1)[-1])
        if family:
            found[name] = family
    return found


def prices(catalog: dict[str, Any], names: list[str]) -> dict[str, dict[str, float]]:
    """The catalog's price of each model id it knows, per million input and output tokens,
    found as `families` finds a family (decision 0051)."""
    known: dict[str, dict[str, float]] = {}
    for provider in catalog.values():
        for model_id, model in (provider.get("models") or {}).items():
            cost = model.get("cost") or {}
            if cost.get("input") is None or cost.get("output") is None:
                continue
            price = {"input": cost["input"], "output": cost["output"]}
            known.setdefault(model_id, price)
            known.setdefault(model_id.rsplit("/", 1)[-1], price)
    found = {}
    for name in names:
        price = known.get(name) or known.get(name.rsplit("/", 1)[-1])
        if price:
            found[name] = price
    return found


def plugins() -> list[str]:
    return sorted({item.name for item in registry.available(kind_named("provider"))})


def installed(package: str) -> bool:
    try:
        distribution(package)
    except PackageNotFoundError:
        return False
    return True
