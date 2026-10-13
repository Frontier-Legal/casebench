"""Resolve a citation as written to one corpus document: the corpus searches, the judge picks."""

from dataclasses import dataclass
from typing import Any

from casebench.corpus.corpora import Corpora
from casebench.corpus.routing import Route, as_code, covered, route
from casebench.judge import prompts
from casebench.judge.client import Judge


def _opening(text: str) -> str:
    """The first paragraph, which is where a decision names its court, numbers and parties."""
    return text.strip().split("\n\n", 1)[0]


@dataclass(frozen=True)
class Resolution:
    """`unchecked` when no connected corpus could hold the citation, so it was never searched."""

    document_id: str | None
    reason: str | None
    route: Route = Route.ALL
    unchecked: bool = False


class Resolver:
    def __init__(self, judge: Judge, corpus: Corpora, candidates: int) -> None:
        self.judge = judge
        self.corpus = corpus
        self.candidates = candidates

    def _candidate(self, document_id: str) -> dict[str, Any]:
        raw = self.corpus.raw(document_id)
        return {
            "id": document_id,
            "court": raw.get("court"),
            "date": raw.get("date"),
            "metadata": raw.get("metadata", {}),
            "opening": _opening(str(raw.get("text", ""))),
        }

    def jurisdictions(self) -> list[str] | None:
        """The codes the judge may name for a citation."""
        return covered(self.corpus.configs)

    def resolve(
        self,
        citation: str,
        jurisdiction: object = None,
        kind: str | None = None,
        case_jurisdiction: str | None = None,
    ) -> Resolution:
        """Searched only in the corpora that can hold it (decision 0036). None when the search
        finds nothing or the judge says no candidate is the cited one."""
        routing = route(self.corpus.configs, as_code(jurisdiction), kind, case_jurisdiction)
        if not routing.names:
            where = routing.jurisdiction or "any jurisdiction"
            reason = f"no connected corpus holds {kind or 'documents'} for {where}"
            return Resolution(None, reason, routing.route, unchecked=True)
        found = self.corpus.search(citation, self.candidates, routing.names)
        if not found:
            return Resolution(None, "the corpus search found no document for it", routing.route)
        pick = self.judge.ask(
            prompts.MATCH, prompts.match(citation, [self._candidate(i) for i in found])
        )
        document_id = pick.get("document_id")
        if document_id is None or str(document_id) not in found:
            return Resolution(None, pick.get("reason"), routing.route)
        return Resolution(str(document_id), pick.get("reason"), routing.route)

    def resolve_listed(self, item: dict[str, Any], case_jurisdiction: str | None) -> Resolution:
        """One citation as the judge listed it, with its kind and jurisdiction."""
        return self.resolve(
            str(item["citation"]), item.get("jurisdiction"), item.get("kind"), case_jurisdiction
        )

    def list_citations(self, answer: str) -> list[dict[str, Any]]:
        return self.judge.ask(
            prompts.LIST_CITATIONS, prompts.list_citations(answer, self.jurisdictions())
        )


def cited_documents(
    resolver: Resolver, answer: str, case_jurisdiction: str | None = None
) -> dict[str, str | None]:
    """Each citation in an answer as written, with the corpus document it resolves to."""
    return {
        str(item["citation"]): resolver.resolve_listed(item, case_jurisdiction).document_id
        for item in resolver.list_citations(answer)
    }
