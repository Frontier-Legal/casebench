"""JSON Schema for one Casebench format, generated from the model that defines it."""

import json
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import CoreSchema

DIALECT = "https://json-schema.org/draft/2020-12/schema"


class _Generator(GenerateJsonSchema):
    """Pydantic's schema with its dialect named, and without a title on every field."""

    def field_title_should_be_set(self, schema: Any) -> bool:
        return False

    def generate(self, schema: CoreSchema, mode: Any = "validation") -> dict[str, Any]:
        return {"$schema": DIALECT, **super().generate(schema, mode=mode)}


def schema_of(model: type[BaseModel]) -> dict[str, Any]:
    return model.model_json_schema(schema_generator=_Generator)


def schema_text(model: type[BaseModel]) -> str:
    """The text written to a schema file, the same on every machine."""
    return json.dumps(schema_of(model), ensure_ascii=False, indent=2) + "\n"
