"""Build the target a config describes, through the plugin registry."""

from typing import Any

from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.targets.interface import Target


def target_from_config(config: dict[str, Any]) -> Target:
    """`type` picks the target plugin; the rest of the mapping is its config."""
    if "type" not in config:
        raise ValueError("the target needs a type: python, http or command")
    source = config.get("source")
    settings = {key: value for key, value in config.items() if key != "source"}
    target = registry.load(kind_named("target"), config["type"], source)(**settings)
    if not isinstance(target, Target):
        raise TypeError(f"the {config['type']} target does not meet the target contract")
    return target
