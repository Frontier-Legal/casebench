"""Build a provider from a model's options, refusing a model setting it does not take."""

import inspect
from typing import Any

# The settings a model's options may hold, under one name on every provider (decision 0038).
SETTINGS = ("reasoning_effort", "thinking_budget", "temperature", "max_tokens", "model_fields")


class SettingNotTaken(ValueError):
    """A model's options set something its provider's API does not document."""


def settings_of(options: dict[str, Any]) -> dict[str, Any]:
    """The model settings among a model's options: what a run with it measured."""
    return {name: options[name] for name in SETTINGS if options.get(name) is not None}


def build(plugin: Any, name: str, options: dict[str, Any]) -> Any:
    """The provider, or `SettingNotTaken` naming the settings this provider does take."""
    parameters = inspect.signature(plugin).parameters
    takes_any = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())
    refused = [key for key in options if key not in parameters and not takes_any]
    unsettable = [key for key in refused if key in SETTINGS]
    if unsettable:
        taken = [setting for setting in SETTINGS if setting in parameters]
        raise SettingNotTaken(
            f"the {name} provider takes no {', '.join(unsettable)}; its API documents "
            f"{', '.join(taken) or 'none of the model settings'} (decision 0038)"
        )
    return plugin(**options)
