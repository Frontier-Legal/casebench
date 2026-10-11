"""The jurisdiction adapter contract: how one country's courts write and cite law."""

from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

from casebench.core.model import FrozenRecord
from casebench.corpus.record import DecisionRecord


class CitationKind(StrEnum):
    DECISION = "decision"
    STATUTE = "statute"


class Citation(FrozenRecord):
    """A citation found in text: where it is, what it cites, and its normalised key."""

    text: str
    start: int
    end: int
    kind: CitationKind
    key: str


@runtime_checkable
class JurisdictionAdapter(Protocol):
    """Reads one jurisdiction's decisions. It never fetches them."""

    @property
    def code(self) -> str:
        """The jurisdiction code configs select it by, such as `tr`."""
        ...

    def citations(self, text: str) -> list[Citation]:
        """Every decision and statute citation in the text, in order."""
        ...

    def operative_part(self, record: DecisionRecord) -> tuple[int, int] | None:
        """Where the ruling starts and ends in the decision's text, if it can be found."""
        ...

    def court_level(self, court: str) -> str | None:
        """The court's level, such as `first_instance` or `appellate`."""
        ...

    def statute_version(self, key: str, on: date) -> str | None:
        """The version id of a statute article in force on a date; None if unsupported."""
        ...
