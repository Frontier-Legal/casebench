"""`casebench models`: the model catalog's providers and models, by the ids init takes."""

import json
from pathlib import Path
from typing import Any

import click

from casebench.setup import catalog as model_catalog


def _provider(provider_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": provider_id,
        "name": entry.get("name") or provider_id,
        "key": (entry.get("env") or [None])[0],
        "models": len(entry.get("models") or {}),
    }


def _model(model_id: str, entry: dict[str, Any]) -> dict[str, Any]:
    cost = entry.get("cost") or {}
    return {
        "id": model_id,
        "name": entry.get("name") or model_id,
        "family": entry.get("family"),
        "price_per_million": {"input": cost.get("input"), "output": cost.get("output")},
        "context": (entry.get("limit") or {}).get("context"),
    }


@click.command(name="models")
@click.argument("provider_id", required=False)
@click.option("--json", "as_json", is_flag=True, help="The same as JSON.")
@click.option(
    "--catalog",
    "catalog_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="A saved copy of the model catalog, instead of fetching it.",
)
def models_command(provider_id: str | None, as_json: bool, catalog_path: Path | None) -> None:
    """The providers in the public model catalog, or one provider's models, with the ids
    `casebench init --judge-provider ID --judge-model ID` takes (decision 0044)."""
    found = model_catalog.load(catalog_path)
    if provider_id is None:
        listed = [_provider(key, entry) for key, entry in sorted(found.items())]
    else:
        if provider_id not in found:
            raise click.BadParameter(f"the catalog has no provider {provider_id!r}")
        models = found[provider_id].get("models") or {}
        listed = [_model(key, entry) for key, entry in sorted(models.items())]
    if as_json:
        click.echo(json.dumps(listed, ensure_ascii=False, indent=2))
        return
    for item in listed:
        click.echo(f"{item['id']}  {item['name']}")
