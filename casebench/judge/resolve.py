"""Resolve citations as written to corpus documents: the corpus searches, the judge picks."""

from dataclasses import dataclass
from typing import Any

from casebench.corpus.corpora import Corpora
from casebench.corpus.passage import best_passage
from casebench.corpus.results import SearchResult
from casebench.corpus.routing import Route, as_code, covered, route
from casebench.judge import prompts
from casebench.judge.budget import batches
from casebench.judge.client import Judge, JudgeReplyUnreadable


@dataclass(frozen=True)
class Resolution:
    """`unchecked` when no connected corpus could hold the citation, so it was never searched."""

    document_id: str | None
    reason: str | None
    route: Route = Route.ALL
    unchecked: bool = False


@dataclass(frozen=True)
class _Searched:
    """A citation whose search found candidates, waiting for the judge to pick one."""

    index: int
    citation: str
    found: list[SearchResult]
    route: Route


class Resolver:
    def __init__(self, judge: Judge, corpus: Corpora, candidates: int) -> None:
        self.judge = judge
        self.corpus = corpus
        self.candidates = candidates

    def _candidate(self, result: SearchResult, citation: str) -> dict[str, Any]:
        """What the corpus says about a result; what it leaves out is filled from the stored
        document, and the judge never gets its whole text (decision 0037)."""
        shown: dict[str, Any] = {"id": result.id}
        shown |= {k: v for k, v in result.model_dump().items() if k != "id" and v is not None}
        if result.citation is not None and result.passage is not None:
            return shown
        raw = self.corpus.raw(result.id)
        if result.citation is None:
            shown |= {"court": raw.get("court"), "date": raw.get("date")}
            shown["metadata"] = raw.get("metadata", {})
        if result.passage is None:
            shown["passage"] = best_passage(str(raw.get("text", "")), citation)
        return shown

    def jurisdictions(self) -> list[str] | None:
        """The codes the judge may name for a citation."""
        return covered(self.corpus.configs)

    def _search(self, index: int, item: dict[str, Any], place: str | None) -> Any:
        """A Resolution when nothing can be matched, else the citation with its candidates.
        Searched only in the corpora that can hold it (decision 0036)."""
        citation, kind = str(item["citation"]), item.get("kind")
        routing = route(self.corpus.configs, as_code(item.get("jurisdiction")), kind, place)
        if not routing.names:
            where = routing.jurisdiction or "any jurisdiction"
            reason = f"no connected corpus holds {kind or 'documents'} for {where}"
            return Resolution(None, reason, routing.route, unchecked=True)
        found = self.corpus.search_results(citation, self.candidates, routing.names, kind)
        if not found:
            return Resolution(None, "the corpus search found no document for it", routing.route)
        return _Searched(index, citation, found, routing.route)

    def _match(self, searched: list[_Searched]) -> dict[int, Resolution]:
        """Every citation in as few judge calls as the model's context window allows."""
        shown = {
            s.index: [self._candidate(result, s.citation) for result in s.found] for s in searched
        }

        def asked(number: int, s: _Searched) -> str:
            return prompts.matched_citation(number, s.citation, shown[s.index])

        window = self.judge.config.context_window
        decided: dict[int, Resolution] = {}
        for batch in batches(searched, lambda s: len(asked(0, s)), len(prompts.MATCH), window):
            listed = [asked(number, s) for number, s in enumerate(batch, start=1)]
            reply = self.judge.ask(prompts.MATCH, prompts.match(listed))
            if not isinstance(reply, list):
                raise JudgeReplyUnreadable(f"the judge's matches are not a list: {reply!r}")
            picks = {p.get("citation"): p for p in reply if isinstance(p, dict)}
            for number, s in enumerate(batch, start=1):
                pick = picks.get(number) or {}
                document_id = pick.get("document_id")
                if document_id is None or str(document_id) not in {r.id for r in s.found}:
                    reason = pick.get("reason") or "the judge picked no candidate"
                    decided[s.index] = Resolution(None, reason, s.route)
                else:
                    decided[s.index] = Resolution(str(document_id), pick.get("reason"), s.route)
        return decided

    def resolve_all(
        self, items: list[dict[str, Any]], case_jurisdiction: str | None = None
    ) -> list[Resolution]:
        """Each citation as the judge listed it, with its kind and jurisdiction, searched on
        its own and matched together (decision 0037). None for a citation the search does
        not find or the judge says no candidate is."""
        outcomes = [
            self._search(index, item, case_jurisdiction) for index, item in enumerate(items)
        ]
        decided = self._match([o for o in outcomes if isinstance(o, _Searched)])
        return [decided[o.index] if isinstance(o, _Searched) else o for o in outcomes]

    def resolve(
        self,
        citation: str,
        jurisdiction: object = None,
        kind: str | None = None,
        case_jurisdiction: str | None = None,
    ) -> Resolution:
        item = {"citation": citation, "jurisdiction": jurisdiction, "kind": kind}
        return self.resolve_all([item], case_jurisdiction)[0]

    def list_citations(self, answer: str) -> list[dict[str, Any]]:
        return self.judge.ask(
            prompts.LIST_CITATIONS, prompts.list_citations(answer, self.jurisdictions())
        )


def cited_documents(
    resolver: Resolver, answer: str, case_jurisdiction: str | None = None
) -> dict[str, str | None]:
    """Each citation in an answer as written, with the corpus document it resolves to."""
    items = resolver.list_citations(answer)
    resolved = resolver.resolve_all(items, case_jurisdiction)
    return {str(item["citation"]): r.document_id for item, r in zip(items, resolved, strict=True)}
