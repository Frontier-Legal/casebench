"""The decision record: what every connector yields."""

from datetime import date

from pydantic import Field

from casebench.core.model import Record

REQUIRED_FIELDS = ("id", "jurisdiction", "court", "date", "text")


class DecisionRecord(Record):
    """One court decision or statute, in the shape everything downstream of a connector reads.
    `level` is the court's level when the provider's metadata gives it."""

    id: str
    jurisdiction: str
    court: str
    date: date
    text: str
    level: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
