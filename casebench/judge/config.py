"""The `judge:` section of casebench.yaml."""

from typing import Any

from pydantic import Field

from casebench.core.model import Record

# The model catalog prices tokens per million (models.dev `cost.input`, `cost.output`).
PER_PRICE = 1_000_000


class Price(Record):
    """What a million input and output tokens cost, in US dollars, as the catalog lists them."""

    input: float
    output: float


class JudgeConfig(Record):
    """No default model: the user picks the judge (decision 0026). `candidates` is how many
    search results the judge may match a citation against; provisional, see 0026.
    `context_window` is the model's, in tokens, from the model catalog; a matching call is
    split only when it would not fit (decision 0037). `price` is from the catalog too, so a
    run can say what it cost (decision 0038)."""

    provider: str
    model: str
    options: dict[str, Any] = Field(default_factory=dict)
    provider_source: str | None = None
    candidates: int = 5
    context_window: int | None = None
    price: Price | None = None
