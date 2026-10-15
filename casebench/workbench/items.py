"""The queue's items, what each shows, and what finishing one writes (decision 0050).

An answer to review is a scored result of a run; a court draft is a draft case built from a
decision. Item keys name where the item lives: `answer:RUN:CASE:REPEAT`, `draft:SUITE:CASE`.
"""

import re
from collections import defaultdict
from typing import Any, Literal
from urllib.parse import quote, unquote

from pydantic import BaseModel, Field

from casebench.cases.approve import CannotApprove, FactDecision, approve_draft
from casebench.cases.suite import save
from casebench.core.case import Approval, Case, Fact, ReferenceSource
from casebench.core.score import CitationLabel, Score
from casebench.judge.families import AgentModel
from casebench.report.calibration import (
    CannotRecord,
    LawyerVerdict,
    criterion_verdicts,
    read_reviews,
    record_verdict,
    said,
)
from casebench.runs.log import Result, RunLog
from casebench.runs.spend import steps_cost
from casebench.workbench.sources import SuiteFolder, Workspace
from casebench.workbench.store import FINISHED, Event, Store

ANSWER, DRAFT = "answer", "draft"
CRITERIA, CITATIONS = "criteria", "citation_integrity"
WRONG_CITATIONS = {CitationLabel.MISGROUNDED, CitationLabel.FABRICATED}
# The inputs shown to a reader, in this order, by their name in the case.
SHOWN_INPUTS = ("question", "instruction", "facts", "constraints", "document", "fields")

Verdict = Literal["pass", "fail"]


class NotFound(LookupError):
    """No such item, or it is no longer in the queue."""


class Refused(ValueError):
    """What was sent cannot be recorded; the message says why, for the reader."""


class QueueItem(BaseModel):
    key: str
    kind: Literal["answer", "draft"]
    title: str
    where: str
    task: str
    flags: list[str] = Field(default_factory=list)


class Highlight(BaseModel):
    start: int
    end: int


class Input(BaseModel):
    name: str
    text: str


class FactView(BaseModel):
    id: str
    kind: str
    value: str
    document: str
    quote: str | None = None
    note: str | None = None
    document_id: str | None = None
    highlight: Highlight | None = None


class LawyerView(BaseModel):
    verdict: Verdict
    by: str
    note: str | None = None
    at: str


class CriterionView(BaseModel):
    id: str
    text: str
    weight: int
    kind: str | None = None
    judge: Verdict
    judge_quote: str | None = None
    judge_note: str | None = None
    evidence: list[str] = Field(default_factory=list)
    lawyer: LawyerView | None = None
    judges_disagreed: bool = False


class CitationView(BaseModel):
    citation: str
    claim: str
    label: str
    document_id: str | None = None
    quote: str | None = None
    reason: str | None = None


class ScoreView(BaseModel):
    metric: str
    value: float
    label: str | None = None


class StepView(BaseModel):
    kind: str
    name: str | None = None
    model: str | None = None
    duration_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class Engineering(BaseModel):
    """What only the engineering view shows (decision 0050)."""

    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = Field(
        default=None, description="US dollars the agent's calls cost, when each has a price."
    )
    steps: list[StepView] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class DecisionView(BaseModel):
    id: str
    court: str | None = None
    date: str | None = None
    text: str | None = None


class AnswerItem(BaseModel):
    key: str
    kind: Literal["answer"] = "answer"
    title: str
    where: str
    task: str
    inputs: list[Input]
    answer: str | None
    reference: list[FactView]
    criteria: list[CriterionView]
    citations: list[CitationView]
    scores: list[ScoreView]
    draft: dict[str, Any] | None = None
    held_by: str | None = None
    engineering: Engineering | None = None


class DraftItem(BaseModel):
    key: str
    kind: Literal["draft"] = "draft"
    title: str
    where: str
    task: str
    inputs: list[Input]
    decision: DecisionView | None
    facts: list[FactView]
    draft: dict[str, Any] | None = None
    held_by: str | None = None
    engineering: Engineering | None = None


class GivenVerdict(BaseModel):
    criterion_id: str
    verdict: Verdict
    note: str | None = None


class GivenFact(BaseModel):
    fact_id: str
    decision: Literal["approve", "edit", "reject"]
    value: str | None = None
    reason: str | None = None


class Finished(BaseModel):
    key: str
    message: str


def _key(kind: str, *parts: str) -> str:
    """Each part percent-encoded, so an id may hold any character."""
    return ":".join([kind, *(quote(part, safe="") for part in parts)])


def answer_key(run_id: str, case_id: str, repeat: int) -> str:
    return _key(ANSWER, run_id, case_id, str(repeat))


def draft_key(suite_id: str, case_id: str) -> str:
    return _key(DRAFT, suite_id, case_id)


def _parse(key: str) -> list[str]:
    kind, *parts = key.split(":")
    parts = [unquote(part) for part in parts]
    if kind == ANSWER and len(parts) == 3 and parts[2].isdigit():
        return [kind, *parts]
    if kind == DRAFT and len(parts) == 2:
        return [kind, *parts]
    raise NotFound(f"no item {key}")


def _title(case: Case | None, fallback: str) -> str:
    if case is None:
        return fallback
    inputs = case.task.inputs
    for name in ("question", "instruction"):
        if inputs.get(name):
            return str(inputs[name])
    return f"{case.task.type} case {case.id}"


def _inputs(case: Case | None) -> list[Input]:
    if case is None:
        return []
    inputs = case.task.inputs
    shown = []
    for name in SHOWN_INPUTS:
        value = inputs.get(name)
        if not value:
            continue
        if isinstance(value, dict):
            value = "\n".join(f"{k}: {v}" for k, v in value.items())
        shown.append(Input(name=name, text=str(value)))
    return shown


def _latest(log: RunLog) -> list[Score]:
    sets = log.score_sets()
    return RunLog.read_scores(sets[-1]) if sets else []


def _groups(scores: list[Score]) -> dict[tuple[str, int], list[Score]]:
    grouped: dict[tuple[str, int], list[Score]] = defaultdict(list)
    for score in scores:
        grouped[(score.case_id, score.repeat)].append(score)
    return grouped


def _reviewable(scores: list[Score]) -> bool:
    return any(
        (s.metric == CRITERIA and s.criteria) or (s.metric == CITATIONS and s.citations)
        for s in scores
    )


def _flags(scores: list[Score]) -> list[str]:
    flags = []
    if any(s.disagreements for s in scores):
        flags.append("judges disagreed")
    failed = any(not v.passed for s in scores if s.metric == CRITERIA for v in s.criteria)
    wrong = any(c.label in WRONG_CITATIONS for s in scores for c in s.citations)
    if failed or wrong:
        flags.append("failed")
    return flags


def _all_reviewed(scores: list[Score], reviewed: set[tuple[str, int, str]]) -> bool:
    criteria = [
        (s.case_id, s.repeat, v.criterion_id)
        for s in scores
        if s.metric == CRITERIA
        for v in s.criteria
    ]
    return bool(criteria) and all(item in reviewed for item in criteria)


def queue(workspace: Workspace, store: Store, person: str) -> list[QueueItem]:
    """Items no one has finished, without those others hold: answers where the judges
    disagreed first, then failed ones, then the rest; then court drafts."""
    finished, held = store.finished(), store.held_by_others(person)
    suites = workspace.suites()
    answers: list[tuple[int, QueueItem]] = []
    for log in workspace.runs():
        info = log.info
        suite = suites.get(info.suite_id)
        reviewed = {(r.case_id, r.repeat, r.criterion_id) for r in read_reviews(log.folder)}
        for (case_id, repeat), scores in sorted(_groups(_latest(log)).items()):
            key = answer_key(info.run_id, case_id, repeat)
            if key in finished or key in held or not _reviewable(scores):
                continue
            if _all_reviewed(scores, reviewed):
                continue
            case = suite.case(case_id) if suite else None
            flags = _flags(scores)
            rank = 0 if "judges disagreed" in flags else 1 if "failed" in flags else 2
            item = QueueItem(
                key=key,
                kind=ANSWER,
                title=_title(case, case_id),
                where=f"run {info.run_id}",
                task=scores[0].task_type,
                flags=flags,
            )
            answers.append((rank, item))
    drafts = [
        QueueItem(
            key=draft_key(suite_id, case.id),
            kind=DRAFT,
            title=_title(case, case.id),
            where=f"suite {suite_id}",
            task=case.task.type,
            flags=["court draft"],
        )
        for suite_id, suite in sorted(suites.items())
        for case in suite.cases
        if case.approval is Approval.DRAFT
        and case.reference.source is ReferenceSource.COURT
        and draft_key(suite_id, case.id) not in held
    ]
    return [item for _, item in sorted(answers, key=lambda pair: pair[0])] + drafts


def find_quote(text: str, quote: str) -> Highlight | None:
    """Where the quote is in the text, whitespace aside."""
    start = text.find(quote)
    if start >= 0:
        return Highlight(start=start, end=start + len(quote))
    words = [re.escape(word) for word in quote.split()]
    if not words:
        return None
    found = re.search(r"\s+".join(words), text)
    return Highlight(start=found.start(), end=found.end()) if found else None


def highlight(text: str, fact: Fact) -> Highlight | None:
    span = fact.evidence.span
    if span and 0 <= span[0] < span[1] <= len(text):
        return Highlight(start=span[0], end=span[1])
    return find_quote(text, fact.evidence.quote) if fact.evidence.quote else None


def fact_view(fact: Fact, text: str | None = None) -> FactView:
    return FactView(
        id=fact.id,
        kind=fact.kind,
        value=fact.value,
        document=fact.evidence.doc,
        quote=fact.evidence.quote,
        note=fact.evidence.note,
        document_id=fact.document_id,
        highlight=highlight(text, fact) if text else None,
    )


def _engineering(
    result: Result | None, raw: dict[str, Any], agent_models: list[AgentModel] | None = None
) -> Engineering:
    steps = result.steps if result else []
    return Engineering(
        latency_ms=result.latency_ms if result else None,
        input_tokens=sum(s.input_tokens or 0 for s in steps) or None,
        output_tokens=sum(s.output_tokens or 0 for s in steps) or None,
        cost=steps_cost(steps, agent_models or []) if steps else None,
        steps=[
            StepView(
                kind=s.kind.value,
                name=s.name,
                model=s.model,
                duration_ms=s.duration_ms,
                input_tokens=s.input_tokens,
                output_tokens=s.output_tokens,
            )
            for s in steps
        ],
        raw=raw,
    )


def _answer(
    workspace: Workspace, run_id: str, case_id: str, repeat: int
) -> tuple[RunLog, Case | None, Result | None, list[Score]]:
    log = workspace.run(run_id)
    if log is None:
        raise NotFound(f"no run {run_id}")
    scores = _groups(_latest(log)).get((case_id, repeat))
    if not scores:
        raise NotFound(f"run {run_id} has no scores for case {case_id}, repeat {repeat}")
    suite = workspace.suites().get(log.info.suite_id)
    case = suite.case(case_id) if suite else None
    result = next((r for r in log.results() if r.case_id == case_id and r.repeat == repeat), None)
    return log, case, result, scores


def answer_item(
    workspace: Workspace, store: Store, key: str, person: str, engineering: bool
) -> AnswerItem:
    _, run_id, case_id, repeat = _parse(key)
    log, case, result, scores = _answer(workspace, run_id, case_id, int(repeat))
    criteria_texts = {c.id: c for c in case.reference.criteria} if case else {}
    latest = {(r.case_id, r.repeat, r.criterion_id): r for r in read_reviews(log.folder)}
    disagreed = {d.item for s in scores for d in s.disagreements}
    criteria = [
        CriterionView(
            id=v.criterion_id,
            text=criteria_texts[v.criterion_id].text
            if v.criterion_id in criteria_texts
            else v.criterion_id,
            weight=v.weight,
            kind=v.kind,
            judge=said(v),
            judge_quote=v.quote,
            judge_note=v.note,
            evidence=v.evidence,
            lawyer=_lawyer(latest.get((case_id, int(repeat), v.criterion_id))),
            judges_disagreed=f"criterion {v.criterion_id}" in disagreed,
        )
        for s in scores
        if s.metric == CRITERIA
        for v in s.criteria
    ]
    citations = [
        CitationView(
            citation=c.citation,
            claim=c.claim,
            label=c.label.value,
            document_id=c.document_id,
            quote=c.quote,
            reason=c.reason,
        )
        for s in scores
        for c in s.citations
    ]
    raw = {
        "result": result.model_dump(mode="json") if result else None,
        "scores": [s.model_dump(mode="json") for s in scores],
    }
    return AnswerItem(
        key=key,
        title=_title(case, case_id),
        where=f"run {run_id}",
        task=scores[0].task_type,
        inputs=_inputs(case),
        answer=result.output if result else None,
        reference=[fact_view(f) for f in case.reference.facts] if case else [],
        criteria=criteria,
        citations=citations,
        scores=[ScoreView(metric=s.metric, value=s.value, label=s.label) for s in scores],
        draft=store.draft(key, person),
        held_by=store.holder(key),
        engineering=_engineering(result, raw, workspace.agent_models) if engineering else None,
    )


def _lawyer(review: LawyerVerdict | None) -> LawyerView | None:
    if review is None:
        return None
    return LawyerView(verdict=review.verdict, by=review.by, note=review.note, at=review.at)


def _draft(workspace: Workspace, key: str) -> tuple[SuiteFolder, Case]:
    _, suite_id, case_id = _parse(key)
    suite = workspace.suites().get(suite_id)
    case = suite.case(case_id) if suite else None
    if suite is None or case is None or case.approval is not Approval.DRAFT:
        raise NotFound(f"no court draft {case_id} in suite {suite_id}")
    return suite, case


def draft_item(
    workspace: Workspace, store: Store, key: str, person: str, engineering: bool
) -> DraftItem:
    suite, case = _draft(workspace, key)
    source = case.provenance.source_decision_id if case.provenance else None
    source = source or next((f.evidence.doc for f in case.reference.facts), None)
    record = workspace.decision(source) if source else None
    decision = None
    if source:
        decision = DecisionView(
            id=source,
            court=record.court if record else None,
            date=record.date.isoformat() if record else None,
            text=record.text if record else None,
        )
    text = record.text if record else None
    return DraftItem(
        key=key,
        title=_title(case, case.id),
        where=f"suite {suite.manifest.suite_id}",
        task=case.task.type,
        inputs=_inputs(case),
        decision=decision,
        facts=[fact_view(f, text) for f in case.reference.facts],
        draft=store.draft(key, person),
        held_by=store.holder(key),
        engineering=_engineering(None, {"case": case.model_dump(mode="json")})
        if engineering
        else None,
    )


def item(workspace: Workspace, store: Store, key: str, person: str, engineering: bool):
    if key.startswith(f"{ANSWER}:"):
        return answer_item(workspace, store, key, person, engineering)
    return draft_item(workspace, store, key, person, engineering)


def finish_answer(
    workspace: Workspace, store: Store, key: str, person: str, given: list[GivenVerdict]
) -> Finished:
    """Every verdict is checked before any is written: overruling the judge needs a note."""
    _, run_id, case_id, repeat = _parse(key)
    log, _, _, scores = _answer(workspace, run_id, case_id, int(repeat))
    judged = criterion_verdicts(scores)
    for verdict in given:
        found = judged.get((case_id, int(repeat), verdict.criterion_id))
        if found is None:
            raise Refused(f"this answer has no criterion {verdict.criterion_id}")
        if verdict.verdict != said(found) and not (verdict.note or "").strip():
            raise Refused(
                f"you overrule the judge on {verdict.criterion_id}; add a note saying why"
            )
    events = []
    for verdict in given:
        try:
            review = record_verdict(
                log.folder, case_id, int(repeat), verdict.criterion_id, verdict.verdict, person,
                verdict.note,
            )  # fmt: skip
        except CannotRecord as failure:
            raise Refused(str(failure)) from None
        events.append(
            Event(
                by=person,
                action="verdict",
                item=key,
                subject=verdict.criterion_id,
                before=review.judge,
                after=review.verdict,
                reason=review.note,
            )
        )
    events.append(Event(by=person, action=FINISHED, item=key, subject=case_id))
    store.log(events)
    store.drop_drafts(key)
    store.release(key)
    overruled = sum(1 for e in events if e.action == "verdict" and e.before != e.after)
    message = f"{len(given)} verdict{'' if len(given) == 1 else 's'} recorded"
    if overruled:
        message += f", {overruled} overruling the judge, in place of the judge's in the scores"
    return Finished(key=key, message=message)


def finish_draft(
    workspace: Workspace, store: Store, key: str, person: str, given: list[GivenFact]
) -> Finished:
    suite, case = _draft(workspace, key)
    decisions = [FactDecision(g.fact_id, g.decision, g.value, g.reason) for g in given]
    try:
        approved = approve_draft(case, decisions, person)
    except CannotApprove as failure:
        raise Refused(str(failure)) from None
    cases = [c for c in suite.cases if c.id != case.id]
    if approved is not None:
        cases.insert([c.id for c in suite.cases].index(case.id), approved)
    old, manifest = save(suite.folder, cases)
    before = {f.id: f.value for f in case.reference.facts}
    after = {f.id: f.value for f in approved.reference.facts} if approved else {}
    events = [
        Event(
            by=person,
            action=g.decision,
            item=key,
            subject=g.fact_id,
            before=before.get(g.fact_id),
            after=after.get(g.fact_id),
            reason=g.reason,
        )
        for g in given
    ]
    events.append(
        Event(
            by=person,
            action=FINISHED,
            item=key,
            subject=case.id,
            before=old,
            after=manifest.content_hash,
        )
    )
    store.log(events)
    store.drop_drafts(key)
    store.release(key)
    if approved is None:
        return Finished(key=key, message=f"every fact rejected, so {case.id} left the suite")
    return Finished(
        key=key, message=f"{case.id} approved; the suite's hash is now {manifest.content_hash}"
    )
