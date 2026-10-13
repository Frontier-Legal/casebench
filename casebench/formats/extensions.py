"""The `extensions` field: data outside a format, keyed by a domain its author controls."""

from typing import Annotated, Any

from pydantic import Field, StringConstraints

DOMAIN = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"

Extensions = Annotated[
    dict[Annotated[str, StringConstraints(pattern=DOMAIN)], Any],
    Field(
        description=(
            "Data outside this format, under a domain its author controls, such as "
            '{"example.com": {...}}. Never required, and never read by Casebench.'
        ),
        # Pydantic lists the key pattern but leaves other keys open; close them as the
        # model does, so a validator outside Casebench refuses the same keys.
        json_schema_extra={"additionalProperties": False},
    ),
]
