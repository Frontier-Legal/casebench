"""The `judge:` section of casebench.yaml."""

from typing import Any

from pydantic import Field

from casebench.core.model import Record


class JudgeConfig(Record):
    """No default model: the user picks the judge (decision 0026). `candidates` is how many
    search results the judge may match a citation against; provisional, see 0026."""

    provider: str
    model: str
    options: dict[str, Any] = Field(default_factory=dict)
    provider_source: str | None = None
    candidates: int = 5
