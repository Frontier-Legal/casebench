"""The `extract:` section of casebench.yaml: the two extraction models."""

from pydantic import Field, model_validator

from casebench.core.model import Record
from casebench.judge.config import JudgeConfig


class ExtractConfig(Record):
    """Exactly two models, and not the same one twice (decision 0027)."""

    models: list[JudgeConfig] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _two_different_models(self) -> "ExtractConfig":
        first, second = self.models
        if (first.provider, first.model) == (second.provider, second.model):
            raise ValueError("extract.models must name two different models")
        return self
