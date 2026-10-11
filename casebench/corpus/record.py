"""The decision record: what every connector yields and every adapter reads."""

from datetime import date

from pydantic import Field

from casebench.core.model import Record

REQUIRED_FIELDS = ("id", "jurisdiction", "court", "date", "text")


class DecisionRecord(Record):
    """One court decision, in the shape every component downstream of a connector reads."""

    id: str
    jurisdiction: str
    court: str
    date: date
    text: str
    level: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
