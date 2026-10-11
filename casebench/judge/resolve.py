"""Resolve a citation as written to one corpus document: the corpus searches, the judge picks."""

from dataclasses import dataclass
from typing import Any

from casebench.corpus.binding import Corpus
from casebench.judge import prompts
from casebench.judge.client import Judge


def _opening(text: str) -> str:
    """The first paragraph, which is where a decision names its court, numbers and parties."""
    return text.strip().split("\n\n", 1)[0]


@dataclass(frozen=True)
class Resolution:
    document_id: str | None
    reason: str | None


class Resolver:
    def __init__(self, judge: Judge, corpus: Corpus, candidates: int) -> None:
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

    def resolve(self, citation: str) -> Resolution:
        """None when the search finds nothing or the judge says no candidate is the cited one."""
        found = self.corpus.search(citation, self.candidates)
        if not found:
            return Resolution(None, "the corpus search found no document for it")
        pick = self.judge.ask(
            prompts.MATCH, prompts.match(citation, [self._candidate(i) for i in found])
        )
        document_id = pick.get("document_id")
        if document_id is None or str(document_id) not in found:
            return Resolution(None, pick.get("reason"))
        return Resolution(str(document_id), pick.get("reason"))
