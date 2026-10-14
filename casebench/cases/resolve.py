"""Resolve a lawyer's citations to corpus documents, keeping the ones the corpus does not hold."""

from casebench.core.case import Case
from casebench.judge.resolve import Resolver
from casebench.suites.resolve import CITED_AS, RESOLVED_KINDS

CHECKED = "citation_integrity"


def resolve_case(case: Case, resolver: Resolver) -> Case:
    """Unlike a generated case, nothing is dropped: a citation the corpus does not hold stays as
    the lawyer wrote it. A kind whose citations all resolve gets its score, and a case checked
    against a corpus gets citation integrity (decision 0039)."""
    place = case.provenance.jurisdiction if case.provenance else None
    open_facts = [
        f for f in case.reference.facts if f.kind in RESOLVED_KINDS and f.document_id is None
    ]
    items = [{"citation": f.value, "kind": CITED_AS[f.kind]} for f in open_facts]
    found = dict(zip((f.id for f in open_facts), resolver.resolve_all(items, place), strict=True))
    facts = [
        f.model_copy(update={"document_id": found[f.id].document_id}) if f.id in found else f
        for f in case.reference.facts
    ]
    metrics = list(case.metrics)
    for kind in RESOLVED_KINDS:
        cited = [f for f in facts if f.kind == kind]
        if cited and all(f.document_id for f in cited) and kind not in metrics:
            metrics.append(kind)
    if CHECKED not in metrics:
        metrics.append(CHECKED)
    reference = case.reference.model_copy(update={"facts": facts})
    return case.model_copy(update={"reference": reference, "metrics": metrics})


def unresolved(case: Case) -> list[str]:
    """The citations of a case no corpus document stands for yet."""
    return [
        f.value for f in case.reference.facts if f.kind in RESOLVED_KINDS and f.document_id is None
    ]
