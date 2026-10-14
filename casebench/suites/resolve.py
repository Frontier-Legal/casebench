"""Resolve the court's statutes and precedents to corpus documents as cases are made."""

from collections import Counter, defaultdict

from casebench.core.case import Case
from casebench.judge.resolve import Resolver

RESOLVED_KINDS = ("statute", "precedent")
# The kind of citation the judge names for each kind of fact.
CITED_AS = {"statute": "statute", "precedent": "decision"}


class CaseResolver:
    """Sets each cited authority's document id and drops the ones the corpus does not hold."""

    def __init__(self, resolver: Resolver) -> None:
        self.resolver = resolver
        self.found: dict[tuple[str, str, str | None], str | None] = {}
        self.counts: dict[str, Counter[str]] = defaultdict(Counter)

    def _find(self, case: Case, place: str | None) -> None:
        """The case's authorities not resolved yet, matched in one judge call (decision 0037),
        each searched in the corpora that cover the case's jurisdiction and hold its kind."""
        asked = []
        for fact in case.reference.facts:
            key = (fact.value, fact.kind, place)
            if fact.kind in RESOLVED_KINDS and key not in self.found and key not in asked:
                asked.append(key)
        items = [{"citation": value, "kind": CITED_AS[kind]} for value, kind, _ in asked]
        for key, resolved in zip(asked, self.resolver.resolve_all(items, place), strict=True):
            self.found[key] = resolved.document_id

    def __call__(self, case: Case) -> Case | None:
        """None when none of the case's authorities resolve, so the case is not made."""
        facts = []
        place = case.provenance.jurisdiction if case.provenance else None
        self._find(case, place)
        for fact in case.reference.facts:
            if fact.kind not in RESOLVED_KINDS:
                facts.append(fact)
                continue
            document_id = self.found[(fact.value, fact.kind, place)]
            self.counts[fact.kind]["resolved" if document_id else "dropped"] += 1
            if document_id:
                facts.append(fact.model_copy(update={"document_id": document_id}))
        if not facts:
            return None
        reference = case.reference.model_copy(update={"facts": facts})
        return case.model_copy(update={"reference": reference})

    def report(self) -> dict[str, dict[str, int]]:
        return {kind: dict(counts) for kind, counts in sorted(self.counts.items())}
