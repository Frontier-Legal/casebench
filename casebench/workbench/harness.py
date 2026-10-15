"""One answer's harness: its calls as a waterfall, with the time no call accounts for.

Also the sums per step and per model, the authority funnel by step, and a diff against another
run (decision 0056).
"""

from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, Field

from casebench.capture.assemble import gaps
from casebench.capture.step import Step, StepKind
from casebench.core.case import Case
from casebench.core.score import CitationLabel, Score
from casebench.judge.families import AgentModel
from casebench.report.funnel import as_corpus_ids, gold
from casebench.runs.log import Result, RunLog
from casebench.runs.spend import agent_price, cost
from casebench.workbench.items import NotFound, Refused, latest_scores
from casebench.workbench.sources import Workspace

CITATIONS = "citation_integrity"
# A step this much slower, and by at least this long, is marked slower; tokens likewise.
SLOWER, SLOWER_MS, MORE_TOKENS = 0.10, 50.0, 0.10
ARGUMENTS = 160

Change = Literal["slower", "faster", "more tokens", "fewer tokens", "same", "gone", "new"]


class Bar(BaseModel):
    """`at_ms` is the start from the answer's first start; None for a step without times."""

    number: int
    kind: str
    name: str | None = None
    model: str | None = None
    at_ms: float | None = None
    duration_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = Field(default=None, description="An estimate at the configured price.")
    arguments: str | None = None
    unaccounted: bool = False


class Total(BaseModel):
    """`cost` is None for steps that call no model, and when a model has no price."""

    name: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost: float | None
    duration_ms: float


class Authority(BaseModel):
    """The step numbers at which a gold authority reached each stage; None where it did not,
    and `checked` lists the stages that could be checked at all."""

    document_id: str
    retrieved: int | None = None
    kept: int | None = None
    read: int | None = None
    cited: bool | None = None
    characterised: bool | None = None
    checked: list[str]


class StepDiff(BaseModel):
    step: str
    before_ms: float | None = None
    after_ms: float | None = None
    before_tokens: int | None = None
    after_tokens: int | None = None
    changes: list[Change]


class Harness(BaseModel):
    run_id: str
    case_id: str
    repeat: int
    latency_ms: float | None
    span_ms: float | None = Field(description="From the first start to the last end.")
    unaccounted_ms: float = Field(description="Gaps between steps, and time outside them.")
    outside_ms: float = Field(description="The latency the steps' span does not cover.")
    bars: list[Bar]
    untimed: int = Field(description="Steps recorded without times, listed after the bars.")
    by_step: list[Total]
    by_model: list[Total]
    priced: bool = Field(description="Whether every model call has a price.")
    funnel: list[Authority] | None = Field(
        default=None, description="None when the case has no gold authority."
    )
    funnel_possible: bool = True
    against: str | None = None
    diff: list[StepDiff] = Field(default_factory=list)
    funnel_before: list[Authority] | None = None


def _label(step: Step) -> str:
    return " · ".join(part for part in (step.kind.value, step.name, step.model) if part)


def _arguments(value: Any) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= ARGUMENTS else text[:ARGUMENTS] + "…"


def _price(step: Step, agent_models: list[AgentModel]) -> float | None:
    if step.kind is not StepKind.LLM:
        return None
    return cost(
        agent_price(step.model or "", agent_models), step.input_tokens or 0, step.output_tokens or 0
    )


def _steps(result: Result) -> list[Step]:
    """The steps in start order with the gaps between them; capture's own gap steps when it
    recorded them, else found the same way. Steps without times come last, as recorded."""
    timed = [s for s in result.steps if s.started is not None and s.ended is not None]
    untimed = [s for s in result.steps if s not in timed]
    if not any(s.kind is StepKind.GAP for s in timed):
        timed = timed + gaps(timed)
    timed.sort(key=lambda s: (s.started or 0.0, s.kind is not StepKind.GAP))
    return timed + untimed


def _totals(bars: list[Bar], key) -> list[Total]:
    grouped: dict[str, list[Bar]] = defaultdict(list)
    for bar in bars:
        name = key(bar)
        if name and not bar.unaccounted:
            grouped[name].append(bar)
    out = []
    for name, members in grouped.items():
        costs = [b.cost for b in members if b.kind == StepKind.LLM.value]
        out.append(
            Total(
                name=name,
                calls=len(members),
                input_tokens=sum(b.input_tokens or 0 for b in members),
                output_tokens=sum(b.output_tokens or 0 for b in members),
                cost=None if not costs or None in costs else sum(c for c in costs if c is not None),
                duration_ms=sum(b.duration_ms or 0.0 for b in members),
            )
        )
    return sorted(out, key=lambda t: -t.duration_ms)


def _funnel(
    case: Case | None, result: Result, scores: list[Score]
) -> tuple[list[Authority] | None, bool]:
    if case is None or not gold(case):
        return None, True
    checks = [c for s in scores if s.metric == CITATIONS for c in s.citations]
    cited_ids = {c.document_id for c in checks if c.document_id}
    known = set(gold(case)) | cited_ids
    steps = [s for s in _steps(result) if s.kind is not StepKind.GAP]
    if not any(s.doc_ids_out for s in steps):
        return [], False
    has_rerank = any(s.kind is StepKind.RERANK for s in steps)
    has_checks = any(s.metric == CITATIONS for s in scores)
    checked = ["retrieved", "read"] + (["kept"] if has_rerank else [])
    checked += ["cited", "characterised"] if has_checks else []

    def first(document_id: str, kinds: set[StepKind] | None, inward: bool) -> int | None:
        for number, step in enumerate(steps, start=1):
            if kinds is not None and step.kind not in kinds:
                continue
            ids = step.doc_ids_in if inward else step.doc_ids_out
            if document_id in as_corpus_ids(set(ids), known):
                return number
        return None

    out = []
    for document_id in gold(case):
        labels = [c.label for c in checks if c.document_id == document_id]
        characterised = (
            True
            if CitationLabel.VERIFIED in labels
            else False
            if CitationLabel.MISGROUNDED in labels
            else None
        )
        out.append(
            Authority(
                document_id=document_id,
                retrieved=first(document_id, None, inward=False),
                kept=first(document_id, {StepKind.RERANK}, inward=False) if has_rerank else None,
                read=first(document_id, {StepKind.LLM}, inward=True),
                cited=(document_id in cited_ids) if has_checks else None,
                characterised=characterised if has_checks else None,
                checked=checked,
            )
        )
    return out, True


def _bars(result: Result, agent_models: list[AgentModel]) -> list[Bar]:
    steps = _steps(result)
    starts = [s.started for s in steps if s.started is not None]
    origin = min(starts) if starts else None
    return [
        Bar(
            number=number,
            kind=step.kind.value,
            name=step.name,
            model=step.model,
            at_ms=round((step.started - origin) * 1000, 1)
            if step.started is not None and origin is not None
            else None,
            duration_ms=step.duration_ms
            if step.duration_ms is not None
            else round((step.ended - step.started) * 1000, 1)
            if step.started is not None and step.ended is not None
            else None,
            input_tokens=step.input_tokens,
            output_tokens=step.output_tokens,
            cost=_price(step, agent_models),
            arguments=_arguments(step.arguments),
            unaccounted=step.kind is StepKind.GAP,
        )
        for number, step in enumerate(steps, start=1)
    ]


def _key(bar: Bar) -> tuple[str, str, str]:
    return (bar.kind, bar.name or "", bar.model or "")


def _diff(before: list[Bar], after: list[Bar]) -> list[StepDiff]:
    """Steps matched by kind, name and model, in order of occurrence."""

    def keyed(bars: list[Bar]) -> dict[tuple[tuple[str, str, str], int], Bar]:
        seen: dict[tuple[str, str, str], int] = defaultdict(int)
        out = {}
        for bar in bars:
            if bar.unaccounted:
                continue
            out[(_key(bar), seen[_key(bar)])] = bar
            seen[_key(bar)] += 1
        return out

    old, new = keyed(before), keyed(after)
    order = list(dict.fromkeys([*new, *old]))
    rows = []
    for key in order:
        a, b = old.get(key), new.get(key)
        name = " · ".join(part for part in key[0] if part) + (f" #{key[1] + 1}" if key[1] else "")
        tokens = [
            (bar.input_tokens or 0) + (bar.output_tokens or 0)
            if bar and (bar.input_tokens is not None or bar.output_tokens is not None)
            else None
            for bar in (a, b)
        ]
        changes: list[Change] = []
        if a is None:
            changes = ["new"]
        elif b is None:
            changes = ["gone"]
        else:
            ta, tb = a.duration_ms, b.duration_ms
            if ta is not None and tb is not None:
                if tb - ta >= SLOWER_MS and tb >= ta * (1 + SLOWER):
                    changes.append("slower")
                elif ta - tb >= SLOWER_MS and ta >= tb * (1 + SLOWER):
                    changes.append("faster")
            na, nb = tokens
            if na and nb is not None:
                if nb >= na * (1 + MORE_TOKENS):
                    changes.append("more tokens")
                elif na >= nb * (1 + MORE_TOKENS):
                    changes.append("fewer tokens")
            changes = changes or ["same"]
        rows.append(
            StepDiff(
                step=name,
                before_ms=a.duration_ms if a else None,
                after_ms=b.duration_ms if b else None,
                before_tokens=tokens[0],
                after_tokens=tokens[1],
                changes=changes,
            )
        )
    return rows


def _answer(log: RunLog, case_id: str, repeat: int) -> Result:
    found = [r for r in log.results() if r.case_id == case_id and r.repeat == repeat]
    if not found:
        raise NotFound(f"run {log.info.run_id} has no answer to case {case_id}, repeat {repeat}")
    return found[-1]


def harness(
    workspace: Workspace, run_id: str, case_id: str, repeat: int, against: str | None = None
) -> Harness:
    log = workspace.run(run_id)
    if log is None:
        raise NotFound(f"no run {run_id}")
    result = _answer(log, case_id, repeat)
    suite = workspace.suites().get(log.info.suite_id)
    case = suite.case(case_id) if suite else None
    scores = [s for s in latest_scores(log) if (s.case_id, s.repeat) == (case_id, repeat)]
    bars = _bars(result, workspace.agent_models)
    timed = [b for b in bars if b.at_ms is not None]
    span = max(((b.at_ms or 0.0) + (b.duration_ms or 0.0) for b in timed), default=None)
    outside = max(0.0, (result.latency_ms or 0.0) - span) if span is not None else 0.0
    inside = sum(b.duration_ms or 0.0 for b in bars if b.unaccounted)
    funnel, possible = _funnel(case, result, scores)
    priced = all(b.cost is not None for b in bars if b.kind == StepKind.LLM.value)
    out = Harness(
        run_id=run_id,
        case_id=case_id,
        repeat=repeat,
        latency_ms=result.latency_ms,
        span_ms=span,
        unaccounted_ms=round(inside + outside, 1),
        outside_ms=round(outside, 1),
        bars=bars,
        untimed=len(bars) - len(timed),
        by_step=_totals(bars, lambda b: " · ".join(p for p in (b.kind, b.name) if p)),
        by_model=_totals(bars, lambda b: b.model),
        priced=priced,
        funnel=funnel,
        funnel_possible=possible,
    )
    if against is None:
        return out
    other = workspace.run(against)
    if other is None:
        raise NotFound(f"no run {against}")
    if other.info.suite_hash != log.info.suite_hash:
        raise Refused("the two runs ran different suites; compare runs of one suite")
    earlier = _answer(other, case_id, repeat)
    earlier_scores = [s for s in latest_scores(other) if (s.case_id, s.repeat) == (case_id, repeat)]
    return out.model_copy(
        update={
            "against": against,
            "diff": _diff(_bars(earlier, workspace.agent_models), bars),
            "funnel_before": _funnel(case, earlier, earlier_scores)[0],
        }
    )
