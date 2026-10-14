"""A data provider profile: a reviewed, saved answer to `casebench corpus add` (decision 0033)."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from casebench.core.jurisdiction import Jurisdiction
from casebench.core.model import Record
from casebench.formats.extensions import Extensions
from casebench.formats.version import FormatVersion

FORMAT = FormatVersion("profile", 1, 0)


class Metered(StrEnum):
    """What the provider charges for, so Casebench can say what a check will spend."""

    SEARCH = "search"
    FETCH = "fetch"
    NONE = "none"


class Profile(Record):
    """How to reach one provider's documents with a built-in connector, or with a connector
    plugin named here. `options` are exactly what `corpus add` would write, with `${VAR}`
    standing in for the key; `probe` is a search the provider knows finds a document."""

    format: str = Field(pattern=FORMAT.pattern)
    name: str
    jurisdictions: list[Jurisdiction] = Field(default_factory=list)
    docs: str | None = None
    terms: str | None = None
    key_env: str | None = Field(
        default=None, description="The environment variable that holds the user's key."
    )
    metered: Metered = Metered.NONE
    maintainer: str | None = Field(
        default=None,
        description="Who answers issues about this profile; required for a bundled one.",
    )
    connector: str
    options: dict[str, Any]
    search_filters: dict[Literal["statute", "decision"], dict[str, Any]] = Field(
        default_factory=dict,
        description="What a search for each kind of citation adds, such as a document type, so "
        "a statute is searched only among statutes (decision 0037).",
    )
    probe: str
    extensions: Extensions = Field(default_factory=dict)
