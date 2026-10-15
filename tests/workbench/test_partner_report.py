"""A run's report for partners: its error rates with their failing answers (decision 0054)."""

import csv
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from casebench.cli import main
from casebench.core.case import (
    Approval,
    Case,
    Criterion,
    Fact,
    Reference,
    ReferenceSource,
    Task,
)
from casebench.core.score import (
    CitationCheck,
    CitationLabel,
    CriterionVerdict,
    Direction,
    Score,
    ScoreKind,
)
from casebench.report.calibration import record_verdict
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.producer import Producer
from casebench.suites.freeze import freeze, load
from casebench.workbench.app import create_app
from casebench.workbench.items import answer_key
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from tests.workbench.test_review_queue import DECISION, HOST, as_, passage, write_corpus

AREAS = {"c1": "labour", "c2": "labour", "c3": "tax", "c4": "tax"}


def case(case_id: str) -> Case:
    """A court case asking for the ruling and the statute, approved by Ayşe."""
    facts = [
        Fact(
            id="outcome-1",
            kind="outcome",
            value="upheld",
            evidence=passage("yerel mahkeme kararını onamıştır"),
        ),
        Fact(
            id="statute-1",
            kind="statute",
            value="4857 sayılı İş Kanunu m. 18",
            evidence=passage("4857 sayılı İş Kanunu m. 18"),
        ),
    ]
    return Case(
        id=case_id,
        task=Task.model_validate({"type": "qa", "question": f"Was dismissal {case_id} valid?"}),
        reference=Reference(
            source=ReferenceSource.COURT,
            facts=facts,
            criteria=[
                Criterion(
                    id="c-outcome-1",
                    text='Passes if the answer concludes that the court ruled "upheld".',
                    weight=1,
                    derived_from=["outcome-1"],
                    kind="outcome",
                )
            ],
            author="Ayşe",
        ),
        metrics=["criteria", "citation_integrity", "outcome", "statute"],
        approval=Approval.APPROVED,
        practice_area=AREAS[case_id],
    )


def scores_for(case_id: str) -> list[Score]:
    """c1 cites a decision that does not exist and one that says something else, and misses
    the ruling; c2 relies on a statute the court did not apply; c3 states the wrong ruling."""
    common: dict[str, Any] = {
        "case_id": case_id,
        "kind": ScoreKind.LLM,
        "direction": Direction.HIGHER,
        "metric_version": "1",
        "task_type": "qa",
        "reference_source": ReferenceSource.COURT,
        "approval": Approval.APPROVED,
        "practice_area": AREAS[case_id],
    }
    verified = CitationCheck(
        citation="Yargıtay 9. HD E. 2019/1 K. 2020/2",
        claim="the dismissal needs a valid reason",
        label=CitationLabel.VERIFIED,
        document_id=DECISION,
    )
    citations = {
        "c1": [
            CitationCheck(
                citation="Yargıtay 3. HD, E. 2021/999",
                claim="see also",
                label=CitationLabel.FABRICATED,
            ),
            CitationCheck(
                citation="Yargıtay 9. HD E. 2019/1 K. 2020/2",
                claim="reinstatement is automatic",
                label=CitationLabel.MISGROUNDED,
                document_id=DECISION,
                reason="the decision says nothing on reinstatement",
            ),
        ],
    }.get(case_id, [verified])
    outcome = {"c3": "wrong outcome"}.get(case_id, "correct")
    statute = {"c2": "wrong statute"}.get(case_id, "correct")
    met = case_id != "c1"
    criterion = CriterionVerdict(
        criterion_id="c-outcome-1",
        weight=1,
        met=met,
        quote="upheld" if met else None,
        kind="outcome",
    )
    return [
        Score(metric="criteria", value=float(met), criteria=[criterion], **common),
        Score(metric="citation_integrity", value=0.5, citations=citations, **common),
        Score(metric="outcome", value=float(outcome == "correct"), label=outcome, **common),
        Score(metric="statute", value=float(statute == "correct"), label=statute, **common),
    ]


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Any]:
    cases = [case(c) for c in AREAS]
    suite = freeze("suite", cases, tmp_path / "suites" / "suite")
    log = RunLog.create(
        tmp_path / "runs" / "r1",
        RunInfo(run_id="r1", suite_id="suite", suite_hash=suite.content_hash, target="agent"),
    )
    for c in cases:
        log.append(Result(case_id=c.id, output=f"The court upheld it in {c.id}."))
    log.write_score_set([s for c in AREAS for s in scores_for(c)], Producer(metrics={}))
    workspace = Workspace(
        tmp_path / "runs", [tmp_path / "suites"], write_corpus(tmp_path / "decisions")
    )
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    return {"tmp": tmp_path, "workspace": workspace, "store": store, "log": log}


def client(project: dict[str, Any]) -> TestClient:
    app = create_app(project["workspace"], project["store"], [HOST])
    return TestClient(app, base_url=f"http://{HOST}")


def test_error_breakdown(project: dict[str, Any]):
    app = client(project)
    app.put("/api/me", json={"name": "Ayşe", "view": "review"})
    listed = app.get("/api/runs", headers=as_("Ayşe")).json()
    before = app.get("/api/runs/r1/report", headers=as_("Ayşe")).json()
    # A lawyer finds c1 does reach the ruling; the judge's verdict no longer counts.
    record_verdict(project["log"].folder, "c1", 0, "c-outcome-1", "pass", "Can", "it says so")
    after = app.get("/api/runs/r1/report", headers=as_("Ayşe")).json()
    opened = app.get(f"/api/items/{answer_key('r1', 'c1', 0)}", headers=as_("Ayşe")).json()

    assert listed == [{"run_id": "r1", "suite_id": "suite", "target": "agent", "scored": True}]
    rates = {r["error"]: r for r in before["rates"]}
    assert list(rates) == [
        "fabricated citation", "unsupported claim", "wrong outcome", "wrong statute",
    ]  # fmt: skip
    shown = {
        name: (r["n"], r["rate"], [f["case_id"] for f in r["failing"]]) for name, r in rates.items()
    }
    assert shown == {
        "fabricated citation": (4, 0.25, ["c1"]),
        "unsupported claim": (4, 0.25, ["c1"]),
        "wrong outcome": (4, 0.5, ["c1", "c3"]),
        "wrong statute": (4, 0.25, ["c2"]),
    }
    for rate in rates.values():
        assert rate["low"] <= rate["rate"] <= rate["high"]
    [fabricated] = rates["fabricated citation"]["failing"]
    assert fabricated["key"] == answer_key("r1", "c1", 0)
    assert fabricated["title"] == "Was dismissal c1 valid?"
    wrong = next(r for r in after["rates"] if r["error"] == "wrong outcome")
    assert [f["case_id"] for f in wrong["failing"]] == ["c3"]
    # The failing answer opens with its question, the answer and the court record.
    assert opened["inputs"][0]["text"] == "Was dismissal c1 valid?"
    assert opened["answer"] == "The court upheld it in c1."
    outcome = next(f for f in opened["reference"] if f["kind"] == "outcome")
    assert (
        outcome["quote"] == "yerel mahkeme kararını onamıştır" and outcome["document"] == DECISION
    )
    labels = [c["label"] for c in opened["citations"]]
    assert labels == ["fabricated", "misgrounded"]


def test_a_case_names_its_practice_area_and_approver(tmp_path: Path):
    """The spreadsheet's practice area column and its author reach the case; a case approved
    before the approver was recorded names its reference's author; a case without either keeps
    its bytes, so its suite keeps its hash (decision 0054)."""
    sheet = tmp_path / "cases.csv"
    with sheet.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["question", "key points", "practice area"])
        writer.writerow(["Is overtime compulsory?", "+1 Says it needs consent", "labour"])
    imported = CliRunner().invoke(
        main,
        ["import", str(sheet), "--suite", str(tmp_path / "suite"), "--by", "Ayşe", "--task",
         "qa", "--config", str(tmp_path / "none.yaml")],
    )  # fmt: skip
    _, [written] = load(tmp_path / "suite")
    older = case("c1").model_copy(update={"practice_area": None})
    first = freeze("old", [older], tmp_path / "old")
    again = freeze("old", load(tmp_path / "old")[1], tmp_path / "old")

    assert imported.exit_code == 0, imported.output
    assert (written.practice_area, written.approved_by, written.approver) == (
        "labour",
        "Ayşe",
        "Ayşe",
    )
    assert older.approved_by is None and older.approver == "Ayşe"
    assert "practice_area" not in older.model_dump(mode="json")
    assert again.content_hash == first.content_hash
