"""Say what an extraction would cost before anything is sent (decision 0038)."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from casebench.extract.prompt import EXTRACT, decision_prompt
from casebench.judge.budget import CHARACTERS_PER_TOKEN, tokens
from casebench.judge.config import PER_PRICE, JudgeConfig


@dataclass(frozen=True)
class Estimate:
    """`input_tokens` is per call, from the decisions already cached; None when none is.
    `low` counts the input alone and `high` adds each call's output limit; a model with no
    price leaves both unknown, and one with no output limit leaves `high` unknown."""

    decisions: int
    models: int
    cached: int
    input_tokens: int | None
    low: float | None
    high: float | None
    unpriced: list[str] = field(default_factory=list)
    unbounded: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [
            f"extract: {self.decisions} decisions, {self.decisions * self.models} model calls "
            f"(one per decision for each of the {self.models} models)"
        ]
        if self.input_tokens is None:
            out.append("input: unknown until decisions are fetched; none of this corpus is cached")
        else:
            out.append(
                f"input: about {self.input_tokens} tokens per call, from the {self.cached} "
                "decisions already cached"
            )
        if self.unpriced:
            out.append(f"cost: unknown, {', '.join(self.unpriced)} has no price in the config")
        elif self.low is not None:
            high = f"${self.high:.2f}" if self.high is not None else "no upper bound"
            out.append(f"cost, an estimate: from ${self.low:.2f} (input alone) to {high}")
            if self.unbounded:
                out.append(f"  no upper bound: {', '.join(self.unbounded)} has no max_tokens")
        out += [
            f"tokens are rough: {CHARACTERS_PER_TOKEN} characters per token, and it varies "
            "by language",
            "nothing was sent",
        ]
        return out


def _cached_lengths(folder: Path) -> list[int]:
    """The length of each cached document's text, read from disk alone."""
    lengths = []
    for path in sorted(folder.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and document.get("text"):
            lengths.append(len(str(document["text"])))
    return lengths


def estimate(cache_folder: Path, models: list[JudgeConfig], decisions: int) -> Estimate:
    """No model and no store is called: the input comes from the cache, the prices and
    output limits from the config."""
    lengths = _cached_lengths(cache_folder)
    asked = len(EXTRACT) + len(decision_prompt(""))
    each = tokens(asked + sum(lengths) // len(lengths)) if lengths else None
    names = [f"{m.provider}/{m.model}" for m in models]
    unpriced = [name for name, m in zip(names, models, strict=True) if m.price is None]
    unbounded = [
        name for name, m in zip(names, models, strict=True) if m.options.get("max_tokens") is None
    ]
    low = high = None
    if not unpriced:
        low = sum(decisions * (each or 0) * m.price.input / PER_PRICE for m in models if m.price)
        if not unbounded:
            high = low + sum(
                decisions * int(m.options["max_tokens"]) * m.price.output / PER_PRICE
                for m in models
                if m.price
            )
    return Estimate(
        decisions=decisions,
        models=len(models),
        cached=len(lengths),
        input_tokens=each,
        low=low,
        high=high,
        unpriced=unpriced,
        unbounded=unbounded,
    )
