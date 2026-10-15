"""What a run spent: every model call it recorded, priced per model (decision 0051)."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from casebench.capture.step import Step, StepKind
from casebench.core.model import FrozenRecord
from casebench.judge.config import PER_PRICE, JudgeConfig, Price
from casebench.judge.families import AgentModel
from casebench.judge.memo import MEMO_FILE, usages
from casebench.runs.log import RunLog

Whose = Literal["agent", "judge"]
UNKNOWN_MODEL = "unknown model"
NOT_COUNTED = (
    "Only model calls are counted; search APIs and other services the agent pays for are not."
)


class ModelSpend(FrozenRecord):
    """One model's calls in a run, with their tokens and, when it has a price, their cost."""

    whose: Whose
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost: float | None = Field(default=None, description="US dollars; none without a price.")


class Spend(FrozenRecord):
    """What a run's model calls cost, per model, the agent's apart from the judge's. A total
    adds only priced calls; `unpriced` names every model it leaves out."""

    models: list[ModelSpend]
    agent: float
    judge: float
    total: float
    unpriced: list[str] = Field(default_factory=list)


def matches(step_model: str, listed: str) -> bool:
    """By id, by last path segment, or as a dated version of the listed model."""
    if step_model == listed:
        return True
    short, listed_short = step_model.rsplit("/", 1)[-1], listed.rsplit("/", 1)[-1]
    return short == listed_short or short.startswith(f"{listed_short}-")


def agent_price(model: str, agent_models: list[AgentModel]) -> Price | None:
    return next((m.price for m in agent_models if m.price and matches(model, m.model)), None)


def cost(price: Price | None, input_tokens: int, output_tokens: int) -> float | None:
    if price is None:
        return None
    return (input_tokens * price.input + output_tokens * price.output) / PER_PRICE


def steps_cost(steps: Iterable[Step], agent_models: list[AgentModel]) -> float | None:
    """What one answer's model calls cost, or None when one of them has no price."""
    total = 0.0
    for step in steps:
        if step.kind is not StepKind.LLM:
            continue
        priced = cost(
            agent_price(step.model or "", agent_models),
            step.input_tokens or 0,
            step.output_tokens or 0,
        )
        if priced is None:
            return None
        total += priced
    return total


def _rows(
    whose: Whose, calls: Iterable[tuple[str, int, int]], price_of: dict[str, Price | None]
) -> list[ModelSpend]:
    counted: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for model, input_tokens, output_tokens in calls:
        row = counted[model]
        row[0] += 1
        row[1] += input_tokens
        row[2] += output_tokens
    return [
        ModelSpend(
            whose=whose,
            model=model,
            calls=calls_made,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cost=cost(price_of.get(model), tokens_in, tokens_out),
        )
        for model, (calls_made, tokens_in, tokens_out) in sorted(counted.items())
    ]


def run_spend(log: RunLog, agent_models: list[AgentModel], judges: list[JudgeConfig]) -> Spend:
    agent_calls = [
        (step.model or UNKNOWN_MODEL, step.input_tokens or 0, step.output_tokens or 0)
        for result in log.results()
        for step in result.steps
        if step.kind is StepKind.LLM
    ]
    judge_calls = [
        (
            f"{usage['provider']}/{usage['model']}" if usage else UNKNOWN_MODEL,
            usage.get("input_tokens") or 0,
            usage.get("output_tokens") or 0,
        )
        for usage in usages(log.folder / MEMO_FILE)
    ]
    judge_prices = {f"{j.provider}/{j.model}": j.price for j in judges}
    agent_prices = {model: agent_price(model, agent_models) for model, _, _ in agent_calls}
    rows = _rows("agent", agent_calls, agent_prices) + _rows("judge", judge_calls, judge_prices)
    agent = sum(r.cost or 0.0 for r in rows if r.whose == "agent")
    judge = sum(r.cost or 0.0 for r in rows if r.whose == "judge")
    return Spend(
        models=rows,
        agent=agent,
        judge=judge,
        total=agent + judge,
        unpriced=[f"{r.whose} {r.model}" for r in rows if r.cost is None],
    )
