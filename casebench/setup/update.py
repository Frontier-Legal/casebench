"""Offer an existing setup only what a newer Casebench adds, keeping every other setting."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from casebench.config import CasebenchConfig
from casebench.setup.catalog import entry_for
from casebench.setup.routes import offers
from casebench.setup.scan import Scan


@dataclass(frozen=True)
class Addition:
    """One thing to add: what it is, for the user, and how it changes the config's data."""

    said: str
    apply: Callable[[dict[str, Any]], None]


def _model_blocks(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Every model block as written: `judge:` or `judges:`, and the extraction models."""
    blocks = []
    if isinstance(data.get("judge"), dict):
        blocks.append(("judge", data["judge"]))
    for number, block in enumerate(data.get("judges") or [], start=1):
        blocks.append(("judge" if number == 1 else "second judge", block))
    for number, block in enumerate((data.get("extract") or {}).get("models") or [], start=1):
        blocks.append((f"extraction model {number}", block))
    return blocks


def missing_from_models(data: dict[str, Any]) -> bool:
    return any("price" not in b or "context_window" not in b for _, b in _model_blocks(data))


def model_additions(data: dict[str, Any], catalog: dict[str, Any]) -> list[Addition]:
    """A price and a context window from the catalog, for each model that has none."""
    found = []
    for label, block in _model_blocks(data):
        entry = entry_for(catalog, str(block.get("model", ""))) or {}
        cost, window = entry.get("cost") or {}, (entry.get("limit") or {}).get("context")
        if (
            "price" not in block
            and cost.get("input") is not None
            and cost.get("output") is not None
        ):
            price = {"input": cost["input"], "output": cost["output"]}
            found.append(
                Addition(
                    f"{label} {block['model']}: price ${price['input']} and ${price['output']} a "
                    "million input and output tokens",
                    lambda d, b=block, p=price: b.update(price=p),
                )
            )
        if "context_window" not in block and window:
            found.append(
                Addition(
                    f"{label} {block['model']}: context window of {window} tokens",
                    lambda d, b=block, w=window: b.update(context_window=w),
                )
            )
    return found


def route_additions(data: dict[str, Any], config: CasebenchConfig, scan: Scan) -> list[Addition]:
    """A capture route for each client the config does not route yet."""
    written = (data.get("capture") or {}).get("routes") or []
    routed = {(r.get("upstream"), r.get("env")) for r in written} | {r.get("name") for r in written}
    found = []
    for offer in offers(scan.clients, config.corpora):
        route = offer.route
        if route is None or route["name"] in routed or (route["upstream"], route["env"]) in routed:
            continue

        def add(d: dict[str, Any], r: dict[str, Any] = route) -> None:
            d.setdefault("capture", {}).setdefault("routes", []).append(r)

        found.append(Addition(f"{offer.client.kind} at {offer.client.where}: {offer.note}", add))
    return found
