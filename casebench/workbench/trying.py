"""Try a question on the configured target, within the day's limit in dollars (decision 0052).

The answer's citations are checked as a run checks them, and the agent's and the judge's calls
are counted against the limit.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from casebench.capture.step import StepKind
from casebench.config import CasebenchConfig
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.metrics.loading import build
from casebench.network import release
from casebench.perimeter import enforce
from casebench.runs.log import Result
from casebench.runs.scoring import context_for
from casebench.runs.spend import agent_price, steps_cost
from casebench.targets.sample import send_sample
from casebench.workbench.items import CitationView
from casebench.workbench.store import Event, Store

TRIED = "tried"
TRY_ITEM = "try a question"
CHECKED = "citation_integrity"


class Budget(BaseModel):
    """What trying a question may still spend today, and why it may not, if it may not."""

    target: str | None
    limit: float | None
    spent_today: float
    remaining: float | None
    can_ask: bool
    why_not: str | None = None
    checks_citations: bool


class Tried(BaseModel):
    question: str
    answer: str | None
    error: str | None = None
    citations: list[CitationView] = Field(default_factory=list)
    agent_cost: float | None
    judge_cost: float | None
    cost: float
    unpriced: list[str] = Field(default_factory=list)
    budget: Budget


class Refused(ValueError):
    """Nothing was sent; the message says why."""


@dataclass(frozen=True)
class Asked:
    result: Result
    citations: list[CitationView]
    judge_cost: float | None


class Asker(Protocol):
    async def ask(self, question: str) -> Asked: ...


def target_name(config: CasebenchConfig | None) -> str | None:
    """What a lawyer can call the target: its function, its host, or its kind."""
    target = (config.target if config else None) or {}
    if target.get("entry"):
        return str(target["entry"]).rsplit(":", 1)[-1]
    if target.get("url"):
        return urlsplit(str(target["url"])).hostname
    return target.get("type")


class ConfiguredAsker:
    """Sends the question as `casebench target check` does, inside the config's network
    rules, and checks the answer's citations with the configured judge and corpus."""

    def __init__(self, config: CasebenchConfig) -> None:
        self.config = config

    async def ask(self, question: str) -> Asked:
        enforce(self.config)
        try:
            result = await send_sample(self.config, question)
            citations: list[CitationView] = []
            judge_cost: float | None = 0.0
            if result.output and self.config.judges and self.config.corpora:
                context = context_for(self.config)
                metric = build(CHECKED, context)
                case = Case(
                    id="try",
                    task=Task.model_validate({"type": "qa", "question": question}),
                    reference=Reference(source=ReferenceSource.LAWYER),
                    metrics=[CHECKED],
                )
                verdict = metric.judge(case, result)
                citations = [
                    CitationView(
                        citation=c.citation,
                        claim=c.claim,
                        label=c.label.value,
                        document_id=c.document_id,
                        quote=c.quote,
                        reason=c.reason,
                    )
                    for c in verdict.citations
                ]
                judges = [context.get("judge"), context.get("second_judge")]
                costs = [j.cost for j in judges if j is not None]
                judge_cost = None if None in costs else sum(c for c in costs if c is not None)
            return Asked(result=result, citations=citations, judge_cost=judge_cost)
        finally:
            release()


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def spent_today(store: Store) -> float:
    today = _today()
    return sum(
        float((e.after or {}).get("cost") or 0)
        for e in store.events(TRY_ITEM)
        if e.action == TRIED and e.at.date().isoformat() == today
    )


def budget(config: CasebenchConfig | None, store: Store) -> Budget:
    """Without a limit, a target, or a price for every model it may call, nothing is sent:
    the workbench could not say what a question costs."""
    spent = spent_today(store)
    limit = config.workbench.try_daily_limit_usd if config and config.workbench else None
    checks = bool(config and config.judges and config.corpora)
    why = None
    if config is None or not config.target:
        why = "casebench.yaml configures no target to ask"
    elif limit is None:
        why = (
            "no daily limit is set; the engineer sets workbench: try_daily_limit_usd: in "
            "casebench.yaml"
        )
    elif not config.agent_models or any(m.price is None for m in config.agent_models):
        why = "a model under agent_models has no price, so what a question costs cannot be measured"
    elif checks and any(j.price is None for j in config.judges):
        why = "the judge has no price, so what checking citations costs cannot be measured"
    elif unpriced := _cleared(_unpriced_seen(store), config):
        why = (
            f"the agent called {', '.join(unpriced)}, which has no price; add it under agent_models"
        )
    elif spent >= limit:
        why = f"today's limit of ${limit:.2f} is spent; it resets at midnight UTC"
    return Budget(
        target=target_name(config),
        limit=limit,
        spent_today=spent,
        remaining=None if limit is None else max(0.0, limit - spent),
        can_ask=why is None,
        why_not=why,
        checks_citations=checks,
    )


def _unpriced_seen(store: Store) -> list[str]:
    """Models a tried question called that had no price; until they have one, no more."""
    seen: list[str] = []
    for event in store.events(TRY_ITEM):
        for model in (event.after or {}).get("unpriced") or []:
            if model not in seen:
                seen.append(model)
    return seen


def _cleared(unpriced: list[str], config: CasebenchConfig) -> list[str]:
    return [m for m in unpriced if agent_price(m, config.agent_models) is None]


async def try_question(
    question: str, person: str, config: CasebenchConfig | None, store: Store, asker: Asker | None
) -> Tried:
    question = question.strip()
    if not question:
        raise Refused("write a question first")
    before = budget(config, store)
    if not before.can_ask or config is None or asker is None:
        raise Refused(before.why_not or "nothing to ask")
    asked = await asker.ask(question)
    steps = [s for s in asked.result.steps if s.kind is StepKind.LLM]
    unpriced = _cleared(sorted({s.model or "unknown model" for s in steps}), config)
    agent = steps_cost(steps, config.agent_models) if not unpriced else None
    cost = (agent or 0.0) + (asked.judge_cost or 0.0)
    store.log(
        [
            Event(
                by=person,
                action=TRIED,
                item=TRY_ITEM,
                subject=question[:500],
                after={
                    "cost": cost,
                    "agent": agent,
                    "judge": asked.judge_cost,
                    "unpriced": unpriced,
                },
            )
        ]
    )
    return Tried(
        question=question,
        answer=asked.result.output,
        error=asked.result.error,
        citations=asked.citations,
        agent_cost=agent,
        judge_cost=asked.judge_cost,
        cost=cost,
        unpriced=unpriced,
        budget=budget(config, store),
    )
