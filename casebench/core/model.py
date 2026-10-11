"""Base classes for every record Casebench reads or writes."""

from pydantic import BaseModel, ConfigDict


class Record(BaseModel):
    """A record that rejects unknown fields, so a typo in a hand-written file fails loudly."""

    model_config = ConfigDict(extra="forbid")


class FrozenRecord(BaseModel):
    """An append-only record: once written, it is never changed."""

    model_config = ConfigDict(extra="forbid", frozen=True)
