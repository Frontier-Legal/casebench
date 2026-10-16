"""Ask for one model Casebench calls itself, the judge or an extraction model, from the catalog."""

from typing import Any

import click

from casebench import keys
from casebench.setup.catalog import installed, model_block, offer, plugins, speakers
from casebench.setup.picker import pick

ANOTHER = "\0another"


def _titled(entries: dict[str, Any]) -> list[tuple[str, str]]:
    titled = [(f"{entry.get('name') or key}  ({key})", key) for key, entry in entries.items()]
    return sorted(titled, key=lambda choice: choice[0].casefold())


def choose(
    role: str,
    catalog: dict[str, Any],
    provider_id: str | None,
    model_id: str | None,
    overrides: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """The config block for one model, and what to tell the user about it."""
    provider_id = provider_id or pick(f"{role}: provider", _titled(catalog))
    if provider_id not in catalog:
        raise click.ClickException(f"the model catalog has no provider {provider_id!r}")
    provider = {"id": provider_id, **catalog[provider_id]}
    name, docs = provider.get("name") or provider_id, provider.get("doc") or "its documentation"
    models = provider.get("models") or {}
    if model_id is None:
        choices = [*_titled(models), ("another model id", ANOTHER)]
        model_id = pick(f"{role}: {name} model", choices)
        if model_id == ANOTHER:
            model_id = click.prompt("the model id")
    model = {"id": model_id, **(models.get(model_id) or {})}
    claimed = speakers(provider)
    plugin = (
        claimed[0]
        if claimed
        else pick(f"{role}: which API does {name} speak? ({docs})", [(p, p) for p in plugins()])
    )
    serving = offer(plugin, provider, model)
    options = dict(serving.options)
    for option in serving.missing:
        options[option] = click.prompt(f"{name}'s {option.replace('_', ' ')} ({docs})")
    options.update(overrides)
    notes = [f"{name} · {model_id}, through the {plugin} provider"]
    key = options.get("api_key_env")
    if key:
        notes.append(f"its key is read from {key}, {'set' if keys.get(key) else 'not set'} here")
    for package in serving.packages:
        if installed(package):
            notes.append(f"it uses this project's {package} and the credentials it finds")
        else:
            notes.append(f"{package} is not installed here; add it to the project first")
    return model_block(plugin, model, options), notes
