"""Read a record at the format version its file declares, strictly or leniently (decision 0034)."""

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from casebench.formats.version import FormatVersion, Reading, reading

Model = TypeVar("Model", bound=BaseModel)


def _path(location: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in location)


def read(
    model: type[Model], data: Any, declared: FormatVersion, current: FormatVersion
) -> tuple[Model, list[str]]:
    """The record, and the fields ignored because a newer minor version added them. Any other
    problem fails as it would at a version this Casebench knows."""
    if reading(declared, current) is Reading.STRICT:
        return model.model_validate(data), []
    try:
        return model.model_validate(data), []
    except ValidationError as error:
        unknown = [item for item in error.errors() if item["type"] == "extra_forbidden"]
        if len(unknown) != error.error_count():
            raise
    return model.model_validate(data, extra="ignore"), [_path(item["loc"]) for item in unknown]


def ignored_note(
    where: str, declared: FormatVersion, current: FormatVersion, fields: list[str]
) -> str:
    """One line for every field a lenient read left out, named so the user can upgrade."""
    return (
        f"{where} is {declared}, newer than the {current} this Casebench reads; "
        f"ignored {', '.join(sorted(set(fields)))}"
    )
