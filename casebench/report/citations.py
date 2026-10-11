"""Count verified, misgrounded and fabricated citations across a run."""

from casebench.core.model import FrozenRecord
from casebench.core.score import CitationLabel, Score


class CitationRate(FrozenRecord):
    label: CitationLabel
    count: int
    rate: float


def citation_rates(scores: list[Score]) -> list[CitationRate]:
    """Over citations, not answers: an answer citing five authorities counts five times."""
    checks = [check for score in scores for check in score.citations]
    total = len(checks)
    return [
        CitationRate(
            label=label,
            count=(n := sum(c.label is label for c in checks)),
            rate=n / total if total else 0.0,
        )
        for label in CitationLabel
    ]
