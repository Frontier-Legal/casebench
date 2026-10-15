"""The four errors a partner asks about, each a share of the answers it could occur in.

Each rate lists the answers that have the error (decision 0054).
"""

from collections import defaultdict
from collections.abc import Callable

from casebench.core.model import FrozenRecord
from casebench.core.score import CitationLabel, Score
from casebench.report.statistics import mean, mean_interval

# The built-in metrics and labels the rates read, by name: framework code imports no plugin.
CITATIONS, OUTCOME, STATUTE = "citation_integrity", "outcome", "statute"
NO_OUTCOME = {"wrong outcome", "unreadable outcome"}
WRONG_STATUTE = "wrong statute"


class Answer(FrozenRecord):
    case_id: str
    repeat: int = 0


class ErrorRate(FrozenRecord):
    """`n` counts the answers the error could occur in; `failing` lists those that have it."""

    error: str
    meaning: str
    n: int
    rate: float
    low: float
    high: float
    failing: list[Answer]


Scores = list[Score]


def _citations(scores: Scores) -> list[Score]:
    return [s for s in scores if s.metric == CITATIONS]


def _cites(label: CitationLabel) -> Callable[[Scores], bool | None]:
    def has(scores: Scores) -> bool | None:
        checked = _citations(scores)
        if not checked:
            return None
        return any(c.label is label for s in checked for c in s.citations)

    return has


def _outcome(scores: Scores) -> bool | None:
    """The outcome metric's label, or a criterion asking for the court's or the lawyer's
    outcome; a stated ruling that is not the one wanted, or none, is wrong."""
    labels = [s.label for s in scores if s.metric == OUTCOME]
    verdicts = [v for s in scores for v in s.criteria if v.kind == OUTCOME]
    if not labels and not verdicts:
        return None
    return any(label in NO_OUTCOME for label in labels) or any(not v.passed for v in verdicts)


def _statute(scores: Scores) -> bool | None:
    labels = [s.label or "" for s in scores if s.metric == STATUTE]
    if not labels:
        return None
    return any(WRONG_STATUTE in label for label in labels)


ERRORS: list[tuple[str, str, Callable[[Scores], bool | None]]] = [
    (
        "fabricated citation",
        "cites a decision or statute the corpus does not hold",
        _cites(CitationLabel.FABRICATED),
    ),
    (
        "unsupported claim",
        "cites an authority the corpus holds for something it does not say",
        _cites(CitationLabel.MISGROUNDED),
    ),
    (
        "wrong outcome",
        "does not reach the ruling the court or the lawyer gave: states another, or none",
        _outcome,
    ),
    ("wrong statute", "relies on a statute the court did not apply", _statute),
]


def answers(scores: Scores) -> dict[tuple[str, int], Scores]:
    grouped: dict[tuple[str, int], Scores] = defaultdict(list)
    for score in scores:
        grouped[(score.case_id, score.repeat)].append(score)
    return dict(sorted(grouped.items()))


def error_rates(scores: Scores, suite_id: str = "") -> list[ErrorRate]:
    """Pass the scores with lawyers' verdicts in place of the judge's (decision 0047). An
    error no answer could have is left out."""
    grouped = answers(scores)
    rates = []
    for error, meaning, has in ERRORS:
        found = [(key, has(members)) for key, members in grouped.items()]
        counted = [(key, bool(failed)) for key, failed in found if failed is not None]
        if not counted:
            continue
        values = [float(failed) for _, failed in counted]
        interval = mean_interval(values, suite_id)
        rates.append(
            ErrorRate(
                error=error,
                meaning=meaning,
                n=len(counted),
                rate=mean(values),
                low=interval.low,
                high=interval.high,
                failing=[Answer(case_id=c, repeat=r) for (c, r), failed in counted if failed],
            )
        )
    return rates
