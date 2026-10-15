"""Lawyers' verdicts beside the judge's, counted per kind of criterion (decision 0047).

They are kept in the run's folder, one line each.
"""

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from casebench import keys
from casebench.core.model import FrozenRecord
from casebench.core.score import CriterionVerdict, Score
from casebench.metrics.criteria import label_of, weighted_score

REVIEWS_FILE = "reviews.jsonl"
CRITERIA = "criteria"
# A criterion whose case names no kind of fact for it.
OTHER = "other"

Said = Literal["pass", "fail"]


class LawyerVerdict(FrozenRecord):
    """One lawyer's verdict on one criterion of one result, beside what the judge said."""

    case_id: str
    repeat: int = 0
    criterion_id: str
    verdict: Said
    judge: Said
    note: str | None = Field(default=None, description="Why, when it overrules the judge.")
    by: str
    at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


class Calibration(FrozenRecord):
    """For one kind of criterion: how many verdicts lawyers gave, and how many agreed with
    the judge's in the score set reported."""

    kind: str
    labelled: int
    agreed: int
    overruled: int


def said(verdict: CriterionVerdict) -> Said:
    """The judge's verdict, also when a lawyer's has replaced it."""
    met = verdict.met if verdict.judge_met is None else verdict.judge_met
    passed = met if verdict.weight > 0 else not met
    return "pass" if passed else "fail"


def _met(review: "LawyerVerdict", weight: int) -> bool:
    """A criterion passes when met, or, with a negative weight, when not triggered."""
    passes = review.verdict == "pass"
    return passes if weight > 0 else not passes


def criterion_verdicts(scores: list[Score]) -> dict[tuple[str, int, str], CriterionVerdict]:
    return {
        (score.case_id, score.repeat, verdict.criterion_id): verdict
        for score in scores
        if score.metric == CRITERIA
        for verdict in score.criteria
    }


def read_reviews(folder: Path) -> list[LawyerVerdict]:
    path = folder / REVIEWS_FILE
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [LawyerVerdict.model_validate_json(line) for line in lines if line]


def add_review(folder: Path, verdict: LawyerVerdict) -> None:
    """Appended, and scrubbed of keys like every line a run writes."""
    with (folder / REVIEWS_FILE).open("a", encoding="utf-8") as stream:
        stream.write(keys.scrub(verdict.model_dump_json()) + "\n")


def lawyers_win(scores: list[Score], reviews: list[LawyerVerdict]) -> list[Score]:
    """The scores with each lawyer's latest verdict in place of the judge's, which each
    replaced verdict keeps; a score with a replaced verdict is computed again (0047)."""
    latest = {(r.case_id, r.repeat, r.criterion_id): r for r in reviews}
    out = []
    for score in scores:
        found = [latest.get((score.case_id, score.repeat, v.criterion_id)) for v in score.criteria]
        if score.metric != CRITERIA or not any(found):
            out.append(score)
            continue
        verdicts = [
            v
            if review is None
            else v.model_copy(
                update={
                    "met": _met(review, v.weight),
                    "reviewed_by": review.by,
                    "judge_met": v.met if v.judge_met is None else v.judge_met,
                }
            )
            for v, review in zip(score.criteria, found, strict=True)
        ]
        update = {
            "criteria": verdicts,
            "value": weighted_score(verdicts),
            "label": label_of(verdicts),
        }
        out.append(score.model_copy(update=update))
    return out


def calibration(scores: list[Score], reviews: list[LawyerVerdict]) -> list[Calibration]:
    """A lawyer's latest verdict on each criterion counts once, against the judge's verdict
    in `scores`; a verdict on a result `scores` does not hold is left out."""
    judged = criterion_verdicts(scores)
    latest = {(r.case_id, r.repeat, r.criterion_id): r for r in reviews}
    labelled: dict[str, int] = defaultdict(int)
    agreed: dict[str, int] = defaultdict(int)
    for item, review in latest.items():
        verdict = judged.get(item)
        if verdict is None:
            continue
        kind = verdict.kind or OTHER
        labelled[kind] += 1
        agreed[kind] += review.verdict == said(verdict)
    return [
        Calibration(kind=kind, labelled=n, agreed=agreed[kind], overruled=n - agreed[kind])
        for kind, n in sorted(labelled.items())
    ]
