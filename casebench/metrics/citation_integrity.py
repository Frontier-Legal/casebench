"""Citation integrity: every cited authority found in the corpus and weighed against its claim."""

from typing import Any

from casebench.core.case import Case
from casebench.core.score import CitationCheck, CitationLabel, Direction, ScoreKind
from casebench.corpus.binding import Corpus
from casebench.judge import prompts
from casebench.judge.client import Judge
from casebench.metrics.base import Verdict
from casebench.runs.log import Result


def _opening(text: str) -> str:
    """The first paragraph, which is where a decision names its court, numbers and parties."""
    return text.strip().split("\n\n", 1)[0]


class CitationIntegrity:
    """The share of an answer's citations the corpus holds and that support their claims."""

    name = "citation_integrity"
    version = "1"
    kind = ScoreKind.LLM
    direction = Direction.HIGHER

    def __init__(self, judge: Judge, corpus: Corpus, candidates: int) -> None:
        self.model = judge
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

    def check(self, citation: str, claim: str) -> CitationCheck:
        found = self.corpus.search(citation, self.candidates)
        if not found:
            return CitationCheck(
                citation=citation,
                claim=claim,
                label=CitationLabel.FABRICATED,
                reason="the corpus search found no document for it",
            )
        pick = self.model.ask(
            prompts.MATCH, prompts.match(citation, [self._candidate(i) for i in found])
        )
        document_id = pick.get("document_id")
        if document_id is None or str(document_id) not in found:
            return CitationCheck(
                citation=citation,
                claim=claim,
                label=CitationLabel.FABRICATED,
                reason=pick.get("reason"),
            )
        document = {"id": str(document_id), **self.corpus.raw(str(document_id))}
        weighed = self.model.ask(prompts.WEIGH, prompts.weigh(claim, document))
        label = CitationLabel.VERIFIED if weighed.get("supports") else CitationLabel.MISGROUNDED
        return CitationCheck(
            citation=citation,
            claim=claim,
            label=label,
            document_id=str(document_id),
            quote=weighed.get("quote"),
            reason=weighed.get("reason"),
        )

    def judge(self, case: Case, result: Result) -> Verdict:
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        listed = self.model.ask(prompts.LIST_CITATIONS, prompts.list_citations(result.output))
        checks = [self.check(str(item["citation"]), str(item.get("claim", ""))) for item in listed]
        if not checks:
            return Verdict(value=1.0, label="cites nothing")
        verified = sum(c.label is CitationLabel.VERIFIED for c in checks)
        counts = {label: sum(c.label is label for c in checks) for label in CitationLabel}
        label = ", ".join(f"{n} {lab.value}" for lab, n in counts.items() if n)
        return Verdict(value=verified / len(checks), label=label, citations=checks)
