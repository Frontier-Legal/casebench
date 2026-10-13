"""A format's name and version as a file declares it, and how a file at another version is read."""

import re
from dataclasses import dataclass
from enum import StrEnum

_PARTS = re.compile(r"^casebench\.(?P<name>[a-z]+)/(?P<major>[0-9]+)\.(?P<minor>[0-9]+)$")


class UnreadableFormat(ValueError):
    """The file names no format, another format, or a major version this Casebench cannot read."""


@dataclass(frozen=True)
class FormatVersion:
    """One format at one version, written as `casebench.<name>/<major>.<minor>`."""

    name: str
    major: int
    minor: int

    def __str__(self) -> str:
        return f"casebench.{self.name}/{self.major}.{self.minor}"

    @property
    def pattern(self) -> str:
        """What a file of this format and major version may declare: any minor version."""
        return rf"^casebench\.{self.name}/{self.major}\.[0-9]+$"

    @property
    def file_name(self) -> str:
        return f"{self.major}.{self.minor}.json"

    @classmethod
    def parse(cls, declared: object) -> "FormatVersion":
        match = _PARTS.match(declared) if isinstance(declared, str) else None
        if match is None:
            raise UnreadableFormat(
                f"{declared!r} is not a format; it looks like casebench.<name>/<major>.<minor>"
            )
        return cls(match["name"], int(match["major"]), int(match["minor"]))


class Reading(StrEnum):
    """How strictly a record is read."""

    STRICT = "strict"
    LENIENT = "lenient"


def reading(declared: FormatVersion, current: FormatVersion) -> Reading:
    """A version this Casebench knows is read strictly, so a typo fails loudly. A newer minor
    version only adds fields, so it is read with those fields ignored. Another major version
    is refused (decision 0034)."""
    if declared.name != current.name:
        raise UnreadableFormat(f"expected a casebench.{current.name} file, found {declared}")
    if declared.major != current.major:
        raise UnreadableFormat(
            f"{declared} cannot be read: this Casebench reads "
            f"casebench.{current.name}/{current.major}.x"
        )
    return Reading.LENIENT if declared.minor > current.minor else Reading.STRICT
