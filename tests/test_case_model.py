"""One model for every evaluation case: task, reference, metrics, score."""

from pathlib import Path

from casebench.core.case import (
    Approval,
    Case,
    Criterion,
    Evidence,
    Fact,
    Reference,
    ReferenceSource,
    Task,
)
from casebench.core.score import CriterionVerdict, Direction, Score, ScoreKind
from casebench.metrics.base import Verdict
from casebench.metrics.criteria import WeightedCriteria
from casebench.references.court import AnswerKey, case_from_answer_key
from casebench.report.tables import build_tables
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.rescore import rescore
from casebench.suites.freeze import freeze, load
from casebench.suites.generate import generate


def answer_key(number: int) -> AnswerKey:
    decision = f"decision-{number:03d}"
    return AnswerKey(
        decision_id=decision,
        jurisdiction="xx",
        inputs={"facts": f"Facts of case {number}, up to the operative part."},
        facts=[
            Fact(
                id="outcome",
                kind="outcome",
                value="reversed" if number % 2 else "upheld",
                evidence=Evidence(doc=decision, span=(900, 960)),
            )
        ],
    )


def court_suite(suite_id: str, keys: list[AnswerKey]) -> list[Case]:
    return generate(
        suite_id,
        keys,
        lambda key: case_from_answer_key(key, task="outcome", metrics=["outcome"]),
        key=lambda key: key.decision_id,
        n=5,
    )


def test_frozen_suite(tmp_path: Path):
    keys = [answer_key(number) for number in range(12)]

    cases = court_suite("tr-outcome-2026-10", keys)
    for case in cases:
        assert case.provenance is not None
        assert case.provenance.source_decision_id == case.reference.facts[0].evidence.doc
        assert case.reference.source is ReferenceSource.COURT
        assert case.reference.facts[0].kind == "outcome"

    manifest = freeze("tr-outcome-2026-10", cases, tmp_path / "first")
    assert manifest.suite_id == "tr-outcome-2026-10"
    assert manifest.content_hash.startswith("sha256:")
    assert manifest.case_count == 5

    again = court_suite("tr-outcome-2026-10", list(reversed(keys)))
    second = freeze("tr-outcome-2026-10", again, tmp_path / "second")
    assert [case.id for case in again] == [case.id for case in cases]
    assert second.content_hash == manifest.content_hash
    assert (tmp_path / "first" / "suite.jsonl").read_bytes() == (
        tmp_path / "second" / "suite.jsonl"
    ).read_bytes()

    _, loaded = load(tmp_path / "first")
    assert loaded == cases


def score_row(
    case_id: str, task: str, source: ReferenceSource, approval: Approval, value: float
) -> Score:
    return Score(
        case_id=case_id,
        metric="criteria",
        metric_version="1",
        kind=ScoreKind.LLM,
        direction=Direction.HIGHER,
        value=value,
        task_type=task,
        reference_source=source,
        approval=approval,
    )


def test_every_score_carries_its_source():
    court, lawyer = ReferenceSource.COURT, ReferenceSource.LAWYER
    scores = [
        score_row("qa-1", "qa", court, Approval.APPROVED, 1.0),
        score_row("qa-2", "qa", court, Approval.DRAFT, 0.0),
        score_row("qa-3", "qa", court, Approval.DRAFT, 0.5),
        score_row("draft-1", "drafting", lawyer, Approval.APPROVED, 0.75),
    ]

    tables = build_tables(scores)

    assert [(table.task_type, table.metric) for table in tables] == [
        ("drafting", "criteria"),
        ("qa", "criteria"),
    ]
    qa = tables[1]
    rows = {(row.reference_source, row.approval): (row.n, row.mean) for row in qa.rows}
    assert rows == {
        (court, "lawyer-approved"): (1, 1.0),
        (court, "unreviewed"): (2, 0.25),
    }
    assert tables[0].rows[0].reference_source is lawyer
    serialised = " ".join(table.model_dump_json() for table in tables).lower()
    assert "overall" not in serialised


class ScriptedGrader:
    """Stands in for a judge: says which criteria the output meets, with a quote."""

    kind = ScoreKind.LLM

    def __init__(self, met: dict[str, str]) -> None:
        self.met = met

    def grade(self, case: Case, output: str, criteria: list[Criterion]) -> list[CriterionVerdict]:
        return [
            CriterionVerdict(
                criterion_id=c.id,
                weight=c.weight,
                met=c.id in self.met,
                quote=self.met.get(c.id),
            )
            for c in criteria
        ]


def drafting_case() -> Case:
    evidence = Evidence(doc="nda-17.docx", anchor="9.2")
    return Case(
        id="firm-contracts-0007",
        task=Task.model_validate({"type": "drafting", "instruction": "Flag unusual liability."}),
        reference=Reference(
            source=ReferenceSource.LAWYER,
            author="senior associate",
            facts=[
                Fact(id="f1", kind="issue", value="Uncapped indemnity", evidence=evidence),
                Fact(id="f2", kind="issue", value="No liability cap", evidence=evidence),
            ],
            criteria=[
                Criterion(
                    id="c1", text="Flags clause 9.2 as uncapped", weight=5, derived_from=["f1"]
                ),
                Criterion(id="c2", text="Proposes a cap", weight=3, derived_from=["f2"]),
                Criterion(id="c3", text="Rewrites clause 4", weight=-4, kind="preservation"),
            ],
        ),
        metrics=["criteria"],
        approval=Approval.APPROVED,
    )


def test_weighted_criteria():
    grader = ScriptedGrader(
        {"c1": "Clause 9.2 leaves the indemnity uncapped.", "c3": "Clause 4 now reads: ..."}
    )
    case = drafting_case()

    verdict = WeightedCriteria(grader).judge(case, Result(case_id=case.id, output="..."))

    by_id = {item.criterion_id: item for item in verdict.criteria}
    assert by_id["c1"].passed and by_id["c1"].quote == "Clause 9.2 leaves the indemnity uncapped."
    assert not by_id["c2"].passed and by_id["c2"].quote is None
    assert not by_id["c3"].passed and by_id["c3"].quote == "Clause 4 now reads: ..."
    assert verdict.value == (5 - 4) / (5 + 3)
    assert verdict.label == "failed: c2, c3"


class ExactOutcome:
    name = "outcome"
    kind = ScoreKind.CODE
    direction = Direction.HIGHER

    def __init__(self, version: str) -> None:
        self.version = version

    def judge(self, case: Case, result: Result) -> Verdict:
        expected = case.reference.facts[0].value
        return Verdict(value=float(result.output == expected), label=None)


def test_re_score_without_re_running(tmp_path: Path):
    cases = court_suite("tr-outcome-2026-10", [answer_key(n) for n in range(12)])
    manifest = freeze("tr-outcome-2026-10", cases, tmp_path / "suite")
    info = RunInfo(
        run_id="run-1",
        suite_id=manifest.suite_id,
        suite_hash=manifest.content_hash,
        target="python:agent:answer",
    )
    log = RunLog.create(tmp_path / "runs" / "run-1", info)
    for case in cases:
        log.append(Result(case_id=case.id, output="reversed"))
    # rescore() takes the log, the cases and the metrics; there is no target to call.
    first = rescore(log, cases, [ExactOutcome(version="1")])
    first_bytes = first.read_bytes()
    second = rescore(log, cases, [ExactOutcome(version="2")])

    assert log.score_sets() == sorted([first, second])
    assert first.read_bytes() == first_bytes
    newer = RunLog.read_scores(second)
    assert {item.metric_version for item in newer} == {"2"}
    assert len(newer) == len(cases)
    assert len(log.results()) == len(cases)
