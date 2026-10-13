"""Name every setting two score sets were produced with differently, and the metrics it moves.

A difference makes those metrics not comparable between the two sets (decision 0035).
"""

from collections.abc import Callable
from dataclasses import dataclass

from casebench.runs.producer import JudgeUsed, Producer

ABSENT = "none"


@dataclass(frozen=True)
class Change:
    setting: str
    first: str
    second: str
    moves: frozenset[str]


def _judges(judges: list[JudgeUsed]) -> str:
    named = [
        f"{j.provider}/{j.model} ({j.family} family, {j.candidates} candidates)" for j in judges
    ]
    return ", ".join(named) or ABSENT


def _each(
    setting: str,
    first: dict[str, str],
    second: dict[str, str],
    moves: Callable[[str], frozenset[str]],
) -> list[Change]:
    return [
        Change(f"{setting} {name}", first.get(name, ABSENT), second.get(name, ABSENT), moves(name))
        for name in sorted(first.keys() | second.keys())
        if first.get(name) != second.get(name)
    ]


def changes(first: Producer, second: Producer) -> list[Change]:
    """A newer Casebench moves no figure by itself: a metric that scores differently has a new
    version. Answer keys written by other models move every metric."""
    metrics = {**first.metrics, **second.metrics}
    by_judge = frozenset(name for name, used in metrics.items() if "judge" in used.reads)
    by_corpus = frozenset(name for name, used in metrics.items() if "corpus" in used.reads)
    found: list[Change] = []
    if first.casebench_version != second.casebench_version:
        found.append(
            Change(
                "Casebench version",
                first.casebench_version,
                second.casebench_version,
                frozenset(),
            )
        )
    found += _each(
        "metric",
        {name: used.version for name, used in first.metrics.items()},
        {name: used.version for name, used in second.metrics.items()},
        lambda name: frozenset({name}),
    )
    if first.judges != second.judges:
        found.append(Change("judge", _judges(first.judges), _judges(second.judges), by_judge))
    found += _each("judge prompt", first.prompts, second.prompts, lambda _: by_judge)
    found += _each("corpus", first.corpora, second.corpora, lambda _: by_corpus)
    if first.extracted_by != second.extracted_by:
        a, b = (", ".join(p.extracted_by) or ABSENT for p in (first, second))
        found.append(Change("answer keys extracted by", a, b, frozenset(metrics)))
    return found
