"""Lawyers' blind preferences between two runs' answers, and their sum per practice area.

Each preference is kept in the later run's folder, one line each (decision 0054).
"""

import hashlib
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field
from scipy.stats import binomtest

from casebench import keys
from casebench.core.model import FrozenRecord
from casebench.report.statistics import mean, mean_interval

PREFERENCES_FILE = "preferences.jsonl"

Run = Literal["first", "second"]
Choice = Literal["first", "second", "equal"]
# A win for the second run counts +1, a loss -1, a tie 0.
POINTS: dict[Choice, float] = {"second": 1.0, "first": -1.0, "equal": 0.0}
SIGNIFICANCE = 0.05


class Preference(FrozenRecord):
    """Which of two answers to one case a lawyer preferred, and why. `against` is the first
    run; the file it is in belongs to the second."""

    against: str
    case_id: str
    repeat: int = 0
    shown_as_a: Run = Field(description="Which run's answer was shown as A.")
    choice: Choice
    reason: str
    by: str
    at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


class AreaPreferences(FrozenRecord):
    """The second run against the first in one practice area. `mean` is wins minus losses
    over the pairs compared, with its bootstrap interval; `sign_p` is the exact two-sided sign
    test of wins against losses, ties left out."""

    practice_area: str | None
    n: int
    wins: int
    losses: int
    ties: int
    mean: float
    low: float
    high: float
    sign_p: float

    @property
    def significant(self) -> bool:
        """The interval leaves out 0 and the sign test agrees, so a few pairs that all went
        one way, whose bootstrap interval is a point, are not called significant."""
        return not self.low <= 0.0 <= self.high and self.sign_p < SIGNIFICANCE


def a_is_first(first: str, second: str, case_id: str, repeat: int) -> bool:
    """The same on every reload and for every reader, and different from case to case."""
    digest = hashlib.sha256(f"{first}\n{second}\n{case_id}\n{repeat}".encode()).digest()
    return digest[0] % 2 == 0


def read_preferences(folder: Path) -> list[Preference]:
    path = folder / PREFERENCES_FILE
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Preference.model_validate_json(line) for line in lines if line]


def add_preference(folder: Path, preference: Preference) -> None:
    """Appended, and scrubbed of keys like every line a run writes."""
    with (folder / PREFERENCES_FILE).open("a", encoding="utf-8") as stream:
        stream.write(keys.scrub(preference.model_dump_json()) + "\n")


def latest(preferences: list[Preference], against: str) -> dict[tuple[str, int], Preference]:
    """For each pair, the preference given last; earlier ones stay in the file."""
    return {(p.case_id, p.repeat): p for p in preferences if p.against == against}


def by_area(
    given: dict[tuple[str, int], Preference],
    areas: dict[str, str | None],
    suite_id: str,
) -> list[AreaPreferences]:
    """`areas` maps each case to its practice area; cases without one are summed together."""
    grouped: dict[str | None, list[Choice]] = defaultdict(list)
    for (case_id, _), preference in given.items():
        grouped[areas.get(case_id)].append(preference.choice)
    out = []
    for area in sorted(grouped, key=lambda name: (name is None, name or "")):
        choices = grouped[area]
        points = [POINTS[choice] for choice in choices]
        interval = mean_interval(points, suite_id)
        wins, losses = choices.count("second"), choices.count("first")
        decided = wins + losses
        sign_p = binomtest(wins, decided, 0.5).pvalue if decided else 1.0
        out.append(
            AreaPreferences(
                practice_area=area,
                n=len(choices),
                wins=wins,
                losses=losses,
                ties=choices.count("equal"),
                mean=mean(points),
                low=interval.low,
                high=interval.high,
                sign_p=float(sign_p),
            )
        )
    return out
