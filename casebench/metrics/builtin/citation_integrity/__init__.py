"""Citation integrity: every cited authority found in the corpus and weighed against its claim."""

from casebench.core.case import Case
from casebench.core.score import CitationCheck, CitationLabel, Direction, ScoreKind
from casebench.corpus.corpora import Corpora
from casebench.judge import prompts
from casebench.judge.client import Judge
from casebench.judge.resolve import Resolver
from casebench.metrics.base import Verdict
from casebench.runs.log import Result


class CitationIntegrity:
    """The share of an answer's citations the corpus holds and that support their claims."""

    name = "citation_integrity"
    version = "2"
    kind = ScoreKind.LLM
    direction = Direction.HIGHER

    def __init__(self, judge: Judge, corpus: Corpora, candidates: int, **_: object) -> None:
        self.model = judge
        self.corpus = corpus
        self.resolver = Resolver(judge, corpus, candidates)

    def check(self, citation: str, claim: str) -> CitationCheck:
        resolved = self.resolver.resolve(citation)
        if resolved.document_id is None:
            return CitationCheck(
                citation=citation,
                claim=claim,
                label=CitationLabel.FABRICATED,
                reason=resolved.reason,
            )
        document = {"id": resolved.document_id, **self.corpus.raw(resolved.document_id)}
        weighed = self.model.ask(prompts.WEIGH, prompts.weigh(claim, document))
        label = CitationLabel.VERIFIED if weighed.get("supports") else CitationLabel.MISGROUNDED
        return CitationCheck(
            citation=citation,
            claim=claim,
            label=label,
            document_id=resolved.document_id,
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
