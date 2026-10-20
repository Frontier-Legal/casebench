"""A suite's history: each metric and error rate run by run, by practice area, with its interval,
and the runs whose settings moved a metric (decision 0067)."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from casebench.core.score import Score
from casebench.report.calibration import record_verdict
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.producer import JudgeUsed, MetricUsed, Producer
from casebench.suites.freeze import freeze
from casebench.workbench.app import create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from tests.workbench.test_partner_report import AREAS, case, scores_for
from tests.workbench.test_review_queue import HOST, as_

METRICS = {
    "criteria": MetricUsed(version="1", reads=["judge"]),
    "citation_integrity": MetricUsed(version="2", reads=["corpus", "judge"]),
    "outcome": MetricUsed(version="1"),
    "statute": MetricUsed(version="1"),
}
JUDGE = JudgeUsed(provider="anthropic", model="judge-a", family="claude", candidates=5)
OTHER_JUDGE = JudgeUsed(provider="openai", model="judge-b", family="gpt", candidates=5)
NIGHTS = ["20261017T020000Z", "20261018T020000Z", "20261019T020000Z"]


def right(scores: list[Score], *wrong_cases: str) -> list[Score]:
    """The ruling right on every case but those named."""
    return [
        s.model_copy(
            update={"value": 0.0, "label": "wrong outcome"}
            if s.case_id in wrong_cases
            else {"value": 1.0, "label": "correct"}
        )
        if s.metric == "outcome"
        else s
        for s in scores
    ]


def night(root: Path, run_id: str, stamp: str, scores: list[Score], judge: JudgeUsed) -> RunLog:
    """One nightly run of the suite, scored at the stamp's moment."""
    suite = freeze("suite", [case(c) for c in AREAS], root / "suites" / "suite")
    log = RunLog.create(
        root / "runs" / run_id,
        RunInfo(run_id=run_id, suite_id="suite", suite_hash=suite.content_hash, target="agent"),
    )
    for case_id in AREAS:
        log.append(Result(case_id=case_id, output=f"The court upheld it in {case_id}."))
    written = log.write_score_set(scores, Producer(metrics=METRICS, judges=[judge]))
    written.rename(written.with_name(f"{stamp}-{run_id}.jsonl"))
    return log


@pytest.fixture
def nights(tmp_path: Path) -> dict[str, Any]:
    every = [s for c in AREAS for s in scores_for(c)]
    logs = [
        night(tmp_path, "n1", NIGHTS[0], right(every, "c1", "c3"), JUDGE),
        night(tmp_path, "n2", NIGHTS[1], right(every, "c3"), JUDGE),
        # The third night is judged by another model, which moves the metrics a judge reads.
        night(tmp_path, "n3", NIGHTS[2], right(every), OTHER_JUDGE),
    ]
    workspace = Workspace(tmp_path / "runs", [tmp_path / "suites"])
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    app = create_app(workspace, store, [HOST])
    client = TestClient(app, base_url=f"http://{HOST}")
    client.put("/api/me", json={"name": "Ayşe", "view": "review"})
    return {"client": client, "logs": logs}


def series(history: dict, metric: str, area: str | None) -> dict:
    return next(
        s
        for s in history["series"]
        if s["metric"] == metric and s["practice_area"] == area and s["approval"] == "approved"
    )


def test_history_over_time(nights: dict[str, Any]):
    client = nights["client"]

    suites = client.get("/api/history", headers=as_("Ayşe")).json()
    history = client.get("/api/history/suite", headers=as_("Ayşe")).json()

    assert suites == [{"suite_id": "suite", "runs": 3, "last": "2026-10-19T02:00:00Z"}]
    assert [r["run_id"] for r in history["runs"]] == ["n1", "n2", "n3"]
    assert history["runs"][0]["scored_at"] == "2026-10-17T02:00:00Z"
    outcome = series(history, "outcome", None)
    assert outcome["name"] == "Ruling correct"
    assert [p["mean"] for p in outcome["points"]] == [0.5, 0.75, 1.0]
    for point in outcome["points"]:
        assert point["low"] <= point["mean"] <= point["high"] and point["n"] == 4
    # Each practice area has its own line: tax had c3 wrong until the third night.
    assert [p["mean"] for p in series(history, "outcome", "tax")["points"]] == [0.5, 0.5, 1.0]
    assert [p["mean"] for p in series(history, "outcome", "labour")["points"]] == [0.5, 1.0, 1.0]
    wrong = next(r for r in history["rates"] if r["error"] == "wrong outcome")
    # c1's answer also misses the ruling its criterion asks for, every night.
    assert [p["mean"] for p in wrong["points"]] == [0.5, 0.5, 0.25]
    # A new judge is named on the night it came, and marked on the metrics a judge reads only.
    assert history["runs"][2]["changed"] == ["judge"]
    assert series(history, "criteria", None)["moved"] == ["n3"]
    assert outcome["moved"] == []


def test_a_lawyers_verdict_moves_the_history(nights: dict[str, Any]):
    client = nights["client"]
    before = client.get("/api/history/suite", headers=as_("Ayşe")).json()

    # A lawyer finds c1 does reach the ruling on the first night; the judge said it did not.
    record_verdict(nights["logs"][0].folder, "c1", 0, "c-outcome-1", "pass", "Can", "it says so")
    after = client.get("/api/history/suite", headers=as_("Ayşe")).json()

    assert series(before, "criteria", None)["points"][0]["mean"] == 0.75
    assert series(after, "criteria", None)["points"][0]["mean"] == 1.0


def test_a_suite_with_no_run_has_no_history(nights: dict[str, Any]):
    missing = nights["client"].get("/api/history/other", headers=as_("Ayşe"))
    assert missing.status_code == 404
