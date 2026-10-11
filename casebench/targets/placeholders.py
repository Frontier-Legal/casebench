"""Fill a target's templates with a case's inputs and the environment's secrets."""

import os
import re
import shlex
from collections.abc import Mapping
from string import Template
from typing import Any

WHOLE = re.compile(r"^\{\{(\w+)\}\}$")
INLINE = re.compile(r"\{\{(\w+)\}\}")


class MissingInput(KeyError):
    pass


def _value(inputs: Mapping[str, Any], name: str) -> Any:
    if name not in inputs:
        raise MissingInput(f"the template asks for {name!r}, which this case does not have")
    return inputs[name]


def fill_json(template: Any, inputs: Mapping[str, Any]) -> Any:
    """`"{{name}}"` alone becomes the value with its type; inside text it becomes text."""
    if isinstance(template, str):
        whole = WHOLE.match(template)
        if whole:
            return _value(inputs, whole.group(1))
        return INLINE.sub(lambda m: str(_value(inputs, m.group(1))), template)
    if isinstance(template, list):
        return [fill_json(item, inputs) for item in template]
    if isinstance(template, dict):
        return {key: fill_json(value, inputs) for key, value in template.items()}
    return template


def fill_args(run: str, inputs: Mapping[str, Any]) -> list[str]:
    """Split like a shell, without one, then replace `{name}` inside each argument."""
    arguments = shlex.split(run, posix=os.name != "nt")
    return [
        re.sub(r"\{(\w+)\}", lambda m: str(_value(inputs, m.group(1))), argument)
        for argument in arguments
    ]


def expand_env(values: Mapping[str, str]) -> dict[str, str]:
    """`${VAR}` reads the environment; a variable that is not set is an error."""
    try:
        return {key: Template(value).substitute(os.environ) for key, value in values.items()}
    except KeyError as missing:
        raise KeyError(f"set the environment variable {missing.args[0]}") from None
