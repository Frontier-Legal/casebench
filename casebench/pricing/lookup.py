"""Each model's price, from its seller's own API where it has one, else the public catalog.

OpenRouter lists every model it serves with its price; OpenAI, Anthropic, Google, Bedrock and
Azure publish none through an API, so the public model catalog stands in (decision 0069). The
last lists fetched are kept under `.casebench/` and used when the network is out of reach.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from casebench import network
from casebench.judge.config import PER_PRICE, Price
from casebench.setup import catalog as model_catalog

OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"
OPENROUTER_HOST = "openrouter.ai"
SAVED = Path(".casebench") / "prices.json"


@dataclass
class PriceList:
    """Prices by model id, from each seller and from the catalog, and when they were read."""

    sellers: dict[str, Price] = field(default_factory=dict)
    catalog: dict[str, Price] = field(default_factory=dict)
    read_at: str | None = None

    def price(self, model: str, sold_by_openrouter: bool = False) -> Price | None:
        """A model OpenRouter sells, or whose id is OpenRouter's, at OpenRouter's price;
        any other at the catalog's, found by its id or the id's last segment."""
        if sold_by_openrouter or model in self.sellers:
            found = self.sellers.get(model)
            if found is not None:
                return found
        return self.catalog.get(model) or self.catalog.get(model.rsplit("/", 1)[-1])


def _openrouter() -> dict[str, Price]:
    """OpenRouter's own list: US dollars per token, as strings (its models API, read
    2026-10-21)."""
    with network.client() as client:
        response = client.get(OPENROUTER_MODELS)
    response.raise_for_status()
    found = {}
    for model in response.json().get("data") or []:
        pricing = model.get("pricing") or {}
        try:
            per_input, per_output = float(pricing["prompt"]), float(pricing["completion"])
        except (KeyError, TypeError, ValueError):
            continue
        if per_input >= 0 and per_output >= 0:
            found[model["id"]] = Price(input=per_input * PER_PRICE, output=per_output * PER_PRICE)
    return found


def _catalog() -> dict[str, Price]:
    """The catalog's prices, by every model id and its last segment."""
    found: dict[str, Price] = {}
    for provider in model_catalog.load().values():
        for model_id, model in (provider.get("models") or {}).items():
            cost = model.get("cost") or {}
            if cost.get("input") is None or cost.get("output") is None:
                continue
            price = Price(input=cost["input"], output=cost["output"])
            found.setdefault(model_id, price)
            found.setdefault(model_id.rsplit("/", 1)[-1], price)
    return found


def _saved(path: Path) -> PriceList:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return PriceList()
    return PriceList(
        sellers={k: Price.model_validate(v) for k, v in data.get("sellers", {}).items()},
        catalog={k: Price.model_validate(v) for k, v in data.get("catalog", {}).items()},
        read_at=data.get("read_at"),
    )


def _save(path: Path, prices: PriceList) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "read_at": prices.read_at,
        "sellers": {k: v.model_dump() for k, v in prices.sellers.items()},
        "catalog": {k: v.model_dump() for k, v in prices.catalog.items()},
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def lookup(saved: Path = SAVED) -> PriceList:
    """Both lists, read at once; a list out of reach is taken from the last one saved."""
    last = _saved(saved)
    with ThreadPoolExecutor(max_workers=2) as pool:
        sellers, catalog = pool.submit(_openrouter), pool.submit(_catalog)
    read = PriceList(read_at=datetime.now(UTC).isoformat(timespec="seconds"))
    for name, future in (("sellers", sellers), ("catalog", catalog)):
        try:
            setattr(read, name, future.result())
        except Exception:
            setattr(read, name, getattr(last, name))
    if read.sellers or read.catalog:
        _save(saved, read)
    return read


def saved(path: Path = SAVED) -> PriceList:
    """The last lists looked up, read without the network."""
    return _saved(path)


def openrouter_url(url: Any) -> bool:
    return isinstance(url, str) and OPENROUTER_HOST in url
