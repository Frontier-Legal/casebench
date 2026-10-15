"""Two runs of one suite compared blind, pair by pair, and summed per practice area.

Each pair of answers is shown as A and B, and a preference needs a reason (decision 0054).
"""

from typing import Literal

from pydantic import BaseModel, Field

from casebench.report.preferences import (
    Choice,
    Preference,
    Run,
    a_is_first,
    add_preference,
    by_area,
    latest,
    read_preferences,
)
from casebench.runs.log import Result, RunLog
from casebench.workbench.items import (
    FactView,
    Input,
    NotFound,
    Refused,
    fact_view,
    inputs_of,
    title_of,
)
from casebench.workbench.sources import SuiteFolder, Workspace
from casebench.workbench.store import Event, Store

Shown = Literal["a", "b", "equal"]
PREFERRED = "preferred"


class PairRow(BaseModel):
    case_id: str
    repeat: int
    title: str
    practice_area: str | None = None
    given: bool


class AreaView(BaseModel):
    practice_area: str | None
    n: int
    wins: int
    losses: int
    ties: int
    mean: float
    low: float
    high: float
    sign_p: float
    significant: bool


class Comparison(BaseModel):
    """`wins` are the second run's: the later one, as the reader chose them."""

    first: str
    second: str
    suite_id: str
    pairs: list[PairRow]
    areas: list[AreaView]


class Revealed(BaseModel):
    """Shown only once a preference is given: what it was and which run each answer is."""

    choice: Shown
    reason: str
    by: str
    at: str
    a_run: str
    b_run: str


class Pair(BaseModel):
    """No run, score, cost or judge's verdict appears until a preference is given."""

    case_id: str
    repeat: int
    title: str
    inputs: list[Input]
    reference: list[FactView]
    a: str | None = Field(description="Answer A, or what went wrong instead of an answer.")
    b: str | None
    given: Revealed | None = None


def _logs(workspace: Workspace, first: str, second: str) -> tuple[RunLog, RunLog]:
    logs = workspace.run(first), workspace.run(second)
    if logs[0] is None or logs[1] is None:
        raise NotFound(f"no run {first if logs[0] is None else second}")
    if first == second:
        raise Refused("choose two different runs")
    if logs[0].info.suite_hash != logs[1].info.suite_hash:
        raise Refused("the two runs ran different suites; compare runs of one suite")
    return logs[0], logs[1]


def _answers(log: RunLog) -> dict[tuple[str, int], Result]:
    """The last result for each case and repeat."""
    return {(r.case_id, r.repeat): r for r in log.results()}


def _text(result: Result) -> str | None:
    return result.output if result.output is not None else result.error


def _suite(workspace: Workspace, log: RunLog) -> SuiteFolder | None:
    return workspace.suites().get(log.info.suite_id)


def comparison(workspace: Workspace, first: str, second: str) -> Comparison:
    before, after = _logs(workspace, first, second)
    suite = _suite(workspace, after)
    shared = sorted(_answers(before).keys() & _answers(after).keys())
    given = latest(read_preferences(after.folder), first)
    areas = {c.id: c.practice_area for c in suite.cases} if suite else {}
    pairs = [
        PairRow(
            case_id=case_id,
            repeat=repeat,
            title=title_of(suite.case(case_id) if suite else None, case_id),
            practice_area=areas.get(case_id),
            given=(case_id, repeat) in given,
        )
        for case_id, repeat in shared
    ]
    summed = by_area(given, areas, after.info.suite_id)
    return Comparison(
        first=first,
        second=second,
        suite_id=after.info.suite_id,
        pairs=pairs,
        areas=[AreaView(**a.model_dump(), significant=a.significant) for a in summed],
    )


def _shown(preference: Preference) -> Shown:
    if preference.choice == "equal":
        return "equal"
    return "a" if preference.choice == preference.shown_as_a else "b"


def pair(workspace: Workspace, first: str, second: str, case_id: str, repeat: int) -> Pair:
    before, after = _logs(workspace, first, second)
    earlier, later = (_answers(log).get((case_id, repeat)) for log in (before, after))
    if earlier is None or later is None:
        raise NotFound(f"the two runs did not both answer case {case_id}, repeat {repeat}")
    flipped = not a_is_first(first, second, case_id, repeat)
    a, b = (later, earlier) if flipped else (earlier, later)
    suite = _suite(workspace, after)
    case = suite.case(case_id) if suite else None
    given = latest(read_preferences(after.folder), first).get((case_id, repeat))
    runs = (second, first) if flipped else (first, second)
    return Pair(
        case_id=case_id,
        repeat=repeat,
        title=title_of(case, case_id),
        inputs=inputs_of(case),
        reference=[fact_view(f) for f in case.reference.facts] if case else [],
        a=_text(a),
        b=_text(b),
        given=Revealed(
            choice=_shown(given),
            reason=given.reason,
            by=given.by,
            at=given.at,
            a_run=runs[0],
            b_run=runs[1],
        )
        if given
        else None,
    )


def prefer(
    workspace: Workspace,
    store: Store,
    first: str,
    second: str,
    case_id: str,
    repeat: int,
    shown: Shown,
    reason: str,
    person: str,
) -> Pair:
    """The preference is written to the second run's folder and to the event log."""
    if not reason.strip():
        raise Refused("say why you prefer it; a preference needs a reason")
    _, after = _logs(workspace, first, second)
    pair(workspace, first, second, case_id, repeat)
    shown_as_a: Run = "first" if a_is_first(first, second, case_id, repeat) else "second"
    other: Run = "second" if shown_as_a == "first" else "first"
    choice: Choice = "equal" if shown == "equal" else shown_as_a if shown == "a" else other
    preference = Preference(
        against=first,
        case_id=case_id,
        repeat=repeat,
        shown_as_a=shown_as_a,
        choice=choice,
        reason=reason.strip(),
        by=person,
    )
    add_preference(after.folder, preference)
    store.log(
        [
            Event(
                by=person,
                action=PREFERRED,
                item=f"compare:{first}:{second}:{case_id}:{repeat}",
                subject=case_id,
                after=preference.model_dump(mode="json"),
                reason=preference.reason,
            )
        ]
    )
    return pair(workspace, first, second, case_id, repeat)
