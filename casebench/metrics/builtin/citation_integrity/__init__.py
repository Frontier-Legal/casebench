"""Citation integrity: every cited authority found in the corpus and weighed against its claim."""

from typing import Any

from casebench.core.case import Case
from casebench.core.score import CitationCheck, CitationLabel, Direction, Disagreement, ScoreKind
from casebench.corpus.corpora import Corpora
from casebench.judge import prompts
from casebench.judge.client import Judge
from casebench.judge.resolve import Resolution, Resolver
from casebench.metrics.base import Verdict
from casebench.runs.log import Result


class CitationIntegrity:
    """The share of an answer's citations the corpus holds and that support their claims. With
    two judges, a citation is verified only when both verify it."""

    name = "citation_integrity"
    version = "3"
    kind = ScoreKind.LLM
    direction = Direction.HIGHER

    def __init__(
        self,
        judge: Judge,
        corpus: Corpora,
        candidates: int,
        second_judge: Judge | None = None,
        **_: object,
    ) -> None:
        self.corpus = corpus
        self.resolvers = [Resolver(judge, corpus, candidates)]
        if second_judge is not None:
            self.resolvers.append(Resolver(second_judge, corpus, second_judge.config.candidates))

    def check(
        self, resolver: Resolver, item: dict[str, Any], resolved: Resolution
    ) -> CitationCheck:
        """One judge's verdict on one citation, once it has been matched to a document."""
        citation, claim = str(item["citation"]), str(item.get("claim", ""))
        if resolved.document_id is None:
            unchecked = CitationLabel.UNCHECKED if resolved.unchecked else None
            return CitationCheck(
                citation=citation,
                claim=claim,
                label=unchecked or CitationLabel.FABRICATED,
                reason=resolved.reason,
                routed=resolved.route.value,
            )
        document = {"id": resolved.document_id, **self.corpus.raw(resolved.document_id)}
        weighed = resolver.judge.ask(prompts.WEIGH, prompts.weigh(claim, document))
        label = CitationLabel.VERIFIED if weighed.get("supports") else CitationLabel.MISGROUNDED
        return CitationCheck(
            citation=citation,
            claim=claim,
            label=label,
            document_id=resolved.document_id,
            quote=weighed.get("quote"),
            reason=weighed.get("reason"),
            routed=resolved.route.value,
        )

    def judge(self, case: Case, result: Result) -> Verdict:
        if result.output is None:
            return Verdict(value=0.0, label="no output")
        place = case.provenance.jurisdiction if case.provenance else None
        checks: list[CitationCheck] = []
        disagreements: list[Disagreement] = []
        twice = 0
        # The first judge lists the citations; each judge then decides each one (decision 0035),
        # matching all of them in one call (decision 0037).
        items = self.resolvers[0].list_citations(result.output)
        matched = [resolver.resolve_all(items, place) for resolver in self.resolvers]
        for position, item in enumerate(items):
            each = [
                self.check(resolver, item, resolved[position])
                for resolver, resolved in zip(self.resolvers, matched, strict=True)
            ]
            checks.append(next((c for c in each if c.label is not CitationLabel.VERIFIED), each[0]))
            if len(each) > 1 and each[0].label is not CitationLabel.UNCHECKED:
                twice += 1
                if each[0].label is not each[1].label:
                    first, second = (c.label.value for c in each)
                    disagreements.append(
                        Disagreement(item=each[0].citation, first=first, second=second)
                    )
        if not checks:
            return Verdict(value=1.0, label="cites nothing")
        verified = sum(c.label is CitationLabel.VERIFIED for c in checks)
        counts = {label: sum(c.label is label for c in checks) for label in CitationLabel}
        label = ", ".join(f"{n} {lab.value}" for lab, n in counts.items() if n)
        # An unchecked citation is neither right nor wrong: the share is of those checked, and
        # an answer whose citations could none of them be checked is not marked down.
        checked = len(checks) - counts[CitationLabel.UNCHECKED]
        return Verdict(
            value=verified / checked if checked else 1.0,
            label=label,
            citations=checks,
            judged_twice=twice,
            disagreements=disagreements,
        )
