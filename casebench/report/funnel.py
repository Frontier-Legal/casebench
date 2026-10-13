"""The authority funnel: each court authority followed through the captured steps."""

from collections import Counter

from casebench.capture.step import NO_DIAGNOSTIC, StepKind
from casebench.core.case import Case
from casebench.core.model import FrozenRecord
from casebench.corpus.ids import SEPARATOR
from casebench.runs.log import Result

STAGES = ("retrieved", "kept", "read", "cited")
LABELS = {
    "retrieved": "retrieval_miss",
    "kept": "rerank_drop",
    "read": "not_in_context",
    "cited": "ignored_authority",
}
UNGROUNDED = "ungrounded"


class AuthorityTrace(FrozenRecord):
    """One court authority: which stages it reached; None where a stage could not be checked."""

    document_id: str
    retrieved: bool
    kept: bool | None
    read: bool
    cited: bool | None
    label: str | None


class CaseFunnel(FrozenRecord):
    case_id: str
    diagnostic: bool
    authorities: list[AuthorityTrace]
    ungrounded: list[str]


def gold(case: Case) -> list[str]:
    """The corpus documents the court relied on, as resolved when the suite was made."""
    return sorted({f.document_id for f in case.reference.facts if f.document_id})


def _label(trace: dict[str, bool | None]) -> str | None:
    for stage in STAGES:
        if trace[stage] is False:
            return LABELS[stage]
    return None


def as_corpus_ids(ids: set[str], known: set[str]) -> set[str]:
    """The agent's own ids, as corpus ids: a bare id is the qualified one it is the provider's
    part of, when exactly one known corpus id has that part (decision 0036)."""
    by_part: dict[str, set[str]] = {}
    for qualified in known:
        by_part.setdefault(qualified.partition(SEPARATOR)[2], set()).add(qualified)
    mapped = set()
    for found in ids:
        matches = by_part.get(found, set())
        mapped |= matches if found not in known and len(matches) == 1 else {found}
    return mapped


def case_funnel(case: Case, result: Result, cited: dict[str, str | None] | None) -> CaseFunnel:
    """`cited` maps the answer's citations to corpus documents; None when there is no judge."""
    cited_ids = {d for d in (cited or {}).values() if d is not None}
    known = set(gold(case)) | cited_ids

    def ids(found: set[str]) -> set[str]:
        return as_corpus_ids(found, known)

    returned = ids({i for step in result.steps for i in step.doc_ids_out})
    if not returned:
        return CaseFunnel(case_id=case.id, diagnostic=False, authorities=[], ungrounded=[])
    reranks = [s for s in result.steps if s.kind is StepKind.RERANK]
    kept_ids = ids({i for s in reranks for i in s.doc_ids_out})
    read_ids = ids({i for s in result.steps if s.kind is StepKind.LLM for i in s.doc_ids_in})
    traces = []
    for document_id in gold(case):
        trace: dict[str, bool | None] = {
            "retrieved": document_id in returned,
            "kept": document_id in kept_ids if reranks else None,
            "read": document_id in read_ids,
            "cited": document_id in cited_ids if cited is not None else None,
        }
        traces.append(
            AuthorityTrace(
                document_id=document_id,
                retrieved=bool(trace["retrieved"]),
                kept=trace["kept"],
                read=bool(trace["read"]),
                cited=trace["cited"],
                label=_label(trace),
            )
        )
    ungrounded = sorted(c for c, d in (cited or {}).items() if d is not None and d not in returned)
    return CaseFunnel(case_id=case.id, diagnostic=True, authorities=traces, ungrounded=ungrounded)


class FunnelSummary(FrozenRecord):
    cases: int
    diagnosed: int
    authorities: int
    survived: dict[str, int]
    labels: dict[str, int]
    ungrounded: int
    without_rerank: int
    cited_checked: bool


def summarise(funnels: list[CaseFunnel]) -> FunnelSummary:
    """How many court authorities survive each stage; a stage not checked does not stop one."""
    traces = [t for f in funnels if f.diagnostic for t in f.authorities]
    survived = {}
    alive = traces
    for stage in STAGES:
        alive = [t for t in alive if getattr(t, stage) is not False]
        survived[stage] = len(alive)
    return FunnelSummary(
        cases=len(funnels),
        diagnosed=sum(f.diagnostic for f in funnels),
        authorities=len(traces),
        survived=survived,
        labels=dict(Counter(t.label for t in traces if t.label)),
        ungrounded=sum(len(f.ungrounded) for f in funnels),
        without_rerank=sum(
            1 for f in funnels if f.diagnostic and any(t.kept is None for t in f.authorities)
        ),
        cited_checked=any(t.cited is not None for t in traces),
    )


def funnel_lines(summary: FunnelSummary) -> list[str]:
    if summary.cases == 0:
        return []
    if summary.diagnosed == 0:
        return [f"authority funnel: {NO_DIAGNOSTIC}; no captured step carried document ids"]
    out = [
        f"authority funnel: {summary.authorities} court authorities in {summary.diagnosed} cases "
        f"with captured document ids ({summary.cases - summary.diagnosed} cases had none)"
    ]
    for stage in STAGES:
        if stage == "cited" and not summary.cited_checked:
            out.append("  cited      not checked: it needs a judge and a corpus in the config")
            continue
        count = summary.survived[stage]
        share = count / summary.authorities if summary.authorities else 0.0
        note = ""
        if stage == "kept" and summary.without_rerank:
            note = f"  ({summary.without_rerank} cases had no rerank step)"
        out.append(f"  {stage:<10} {count:>5} {share:>6.0%}{note}")
    if summary.labels:
        out.append("  " + ", ".join(f"{label} {n}" for label, n in sorted(summary.labels.items())))
    out.append(f"  {UNGROUNDED} citations: {summary.ungrounded}")
    out.append("  read means the document's id was in a model call's request")
    return out
