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

    def _document(self, citation: str, kind: str, place: str | None) -> str | None:
        """Searched in the corpora that cover the case's jurisdiction and hold that kind."""
        asked = (citation, kind, place)
        if asked not in self.found:
            resolved = self.resolver.resolve(citation, kind=CITED_AS[kind], case_jurisdiction=place)
            self.found[asked] = resolved.document_id
        return self.found[asked]

    def __call__(self, case: Case) -> Case | None:
        """None when none of the case's authorities resolve, so the case is not made."""
        facts = []
        place = case.provenance.jurisdiction if case.provenance else None
        for fact in case.reference.facts:
            if fact.kind not in RESOLVED_KINDS:
                facts.append(fact)
                continue
            document_id = self._document(fact.value, fact.kind, place)
            self.counts[fact.kind]["resolved" if document_id else "dropped"] += 1
            if document_id:
                facts.append(fact.model_copy(update={"document_id": document_id}))
        if not facts:
            return None
        reference = case.reference.model_copy(update={"facts": facts})
        return case.model_copy(update={"reference": reference})

    def report(self) -> dict[str, dict[str, int]]:
        return {kind: dict(counts) for kind, counts in sorted(self.counts.items())}
