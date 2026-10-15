"""The harness view: one answer's calls as a waterfall, with the funnel and a diff (decision 0056).
That the review view does not offer it is tested with the web app, in harness.test.tsx."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from casebench.capture.step import Step, StepKind
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
from casebench.core.score import CitationCheck, CitationLabel, Direction, Score, ScoreKind
from casebench.judge.config import Price
from casebench.judge.families import AgentModel
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.producer import Producer
from casebench.suites.freeze import freeze
from casebench.workbench.app import create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from tests.workbench.test_review_queue import HOST, as_

T0 = 1_760_000_000.0
DECISION, STATUTE, OTHER = "corpus:tr-1", "corpus:law-18", "corpus:tr-9"
MODEL = "agent-model"


def case() -> Case:
    facts = [
        Fact(id="precedent-1", kind="precedent", value="Yargıtay 9. HD E. 2019/1",
             evidence=Evidence(doc=DECISION, quote="..."), document_id=DECISION),
        Fact(id="statute-1", kind="statute", value="İş Kanunu m. 18",
             evidence=Evidence(doc=DECISION, quote="..."), document_id=STATUTE),
    ]  # fmt: skip
    return Case(
        id="c1",
        task=Task.model_validate({"type": "qa", "question": "Is the dismissal valid?"}),
        reference=Reference(
            source=ReferenceSource.COURT,
            facts=facts,
            criteria=[
                Criterion(id="k1", text="Relies on m. 18", weight=1, derived_from=["statute-1"])
            ],
        ),
        metrics=["criteria", "citation_integrity"],
        approval=Approval.APPROVED,
    )


def llm(n: int, start: float, seconds: float, tokens: int, ids_in: list[str] | None = None):
    return Step(
        kind=StepKind.LLM, name=f"think {n}", provider="anthropic", model=MODEL,
        started=T0 + start, ended=T0 + start + seconds, duration_ms=seconds * 1000,
        input_tokens=tokens, output_tokens=tokens // 10, doc_ids_in=ids_in or [],
    )  # fmt: skip


def tool(name: str, start: float, seconds: float, out: list[str]):
    return Step(
        kind=StepKind.TOOL, name=name, started=T0 + start, ended=T0 + start + seconds,
        duration_ms=seconds * 1000, arguments={"query": "geçerli sebep " * 20}, doc_ids_out=out,
    )  # fmt: skip


def steps_r1() -> list[Step]:
    """Seven model calls and three tool calls; 3.2 seconds between model calls 4 and 5."""
    return [
        llm(1, 0.0, 1.0, 1000),
        tool("search", 1.0, 0.5, ["tr-1", "law-18"]),
        llm(2, 1.5, 1.0, 2000, ["tr-1"]),
        tool("fetch", 2.5, 0.25, ["tr-1"]),
        llm(3, 2.75, 1.0, 3000),
        llm(4, 3.75, 1.0, 3000),
        llm(5, 7.95, 1.0, 3000),
        tool("search", 8.95, 0.5, ["tr-9"]),
        llm(6, 9.45, 1.0, 3000),
        llm(7, 10.45, 1.0, 1000),
    ]


def steps_r2() -> list[Step]:
    """The later run: model call 3 is two seconds slower and uses twice the tokens, and the
    fetch is gone, so the precedent is never read."""
    steps = [s for s in steps_r1() if s.name != "fetch"]
    steps = [s.model_copy(update={"doc_ids_in": []}) if s.name == "think 2" else s for s in steps]
    return [llm(3, 2.75, 3.0, 6000) if s.name == "think 3" else s for s in steps]


def scored(runs: Path, run_id: str, suite_hash: str, steps: list[Step]) -> RunLog:
    log = RunLog.create(
        runs / run_id,
        RunInfo(run_id=run_id, suite_id="suite", suite_hash=suite_hash, target="agent"),
    )
    log.append(Result(case_id="c1", output="Invalid, see m. 18.", steps=steps, latency_ms=12_000))
    check = CitationCheck(
        citation="Yargıtay 9. HD E. 2019/1", claim="valid reason", label=CitationLabel.VERIFIED,
        document_id=DECISION,
    )  # fmt: skip
    score = Score(
        case_id="c1", metric="citation_integrity", metric_version="3", kind=ScoreKind.LLM,
        direction=Direction.HIGHER, value=1.0, citations=[check], task_type="qa",
        reference_source=ReferenceSource.COURT, approval=Approval.APPROVED,
    )  # fmt: skip
    log.write_score_set([score], Producer(metrics={}))
    return log


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Any]:
    suite = freeze("suite", [case()], tmp_path / "suites" / "suite")
    scored(tmp_path / "runs", "r1", suite.content_hash, steps_r1())
    scored(tmp_path / "runs", "r2", suite.content_hash, steps_r2())
    priced = AgentModel(model=MODEL, family="agent", price=Price(input=3.0, output=15.0))
    workspace = Workspace(tmp_path / "runs", [tmp_path / "suites"], None, [priced])
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    return {"workspace": workspace, "store": store}


def get(project: dict[str, Any], url: str, role: str | None = None, view: str = "engineering"):
    app = TestClient(
        create_app(project["workspace"], project["store"], [HOST], role),
        base_url=f"http://{HOST}",
    )
    app.put("/api/me", json={"name": "Can", "view": view})
    return app.get(url, headers=as_("Can"))


def test_waterfall(project: dict[str, Any]):
    shown = get(project, "/api/harness/r1/c1/0").json()

    calls = [b for b in shown["bars"] if not b["unaccounted"]]
    assert [b["kind"] for b in calls].count("llm") == 7
    assert [b["kind"] for b in calls].count("tool") == 3
    assert [b["at_ms"] for b in shown["bars"]] == sorted(b["at_ms"] for b in shown["bars"])
    first = calls[0]
    assert (first["model"], first["duration_ms"], first["input_tokens"]) == (MODEL, 1000.0, 1000)
    assert first["cost"] == pytest.approx((1000 * 3.0 + 100 * 15.0) / 1e6)
    assert calls[1]["arguments"].endswith("…") and calls[1]["cost"] is None
    by_model = {t["name"]: t for t in shown["by_model"]}
    assert by_model[MODEL]["calls"] == 7
    assert by_model[MODEL]["input_tokens"] == 16_000
    assert by_model[MODEL]["duration_ms"] == 7000.0
    by_step = {t["name"]: t for t in shown["by_step"]}
    assert by_step["tool · search"]["calls"] == 2
    assert by_step["tool · search"]["duration_ms"] == 1000.0
    assert shown["priced"] is True


def test_diff_across_runs(project: dict[str, Any]):
    shown = get(project, "/api/harness/r2/c1/0?against=r1").json()

    rows = {row["step"]: row for row in shown["diff"]}
    assert shown["against"] == "r1"
    assert rows["llm · think 3 · agent-model"]["changes"] == ["slower", "more tokens"]
    assert (
        rows["llm · think 3 · agent-model"]["before_ms"],
        rows["llm · think 3 · agent-model"]["after_ms"],
    ) == (1000.0, 3000.0)
    assert rows["tool · fetch"]["changes"] == ["gone"]
    assert rows["llm · think 1 · agent-model"]["changes"] == ["same"]
    before = {a["document_id"]: a for a in shown["funnel_before"]}
    after = {a["document_id"]: a for a in shown["funnel"]}
    assert before[DECISION]["read"] is not None and after[DECISION]["read"] is None


def test_funnel_beside_the_calls(project: dict[str, Any]):
    shown = get(project, "/api/harness/r1/c1/0").json()

    numbers = {b["name"]: b["number"] for b in reversed(shown["bars"]) if b["name"]}
    funnel = {a["document_id"]: a for a in shown["funnel"]}
    precedent, statute = funnel[DECISION], funnel[STATUTE]
    assert precedent["retrieved"] == numbers["search"]
    assert precedent["read"] == numbers["think 2"]
    assert (precedent["cited"], precedent["characterised"]) == (True, True)
    assert statute["retrieved"] == numbers["search"]
    assert (statute["read"], statute["cited"], statute["characterised"]) == (None, False, None)
    # No rerank step, so whether an authority was kept is not checked.
    assert precedent["kept"] is None and "kept" not in precedent["checked"]


def test_gaps_are_honest(project: dict[str, Any]):
    shown = get(project, "/api/harness/r1/c1/0").json()

    [gap] = [b for b in shown["bars"] if b["unaccounted"]]
    after = next(b for b in shown["bars"] if b["number"] == gap["number"] - 1)
    before_next = next(b for b in shown["bars"] if b["number"] == gap["number"] + 1)
    assert gap["duration_ms"] == 3200.0
    assert (after["name"], before_next["name"]) == ("think 4", "think 5")
    # 11.45 s of spans in a 12 s answer: 0.55 s more no step accounts for.
    assert shown["outside_ms"] == pytest.approx(550.0)
    assert shown["unaccounted_ms"] == pytest.approx(3750.0)


def test_hidden_from_reviewers(project: dict[str, Any]):
    locked = get(project, "/api/harness/r1/c1/0", role="reviewer")
    reviewing = get(project, "/api/harness/r1/c1/0", view="review")
    engineering = get(project, "/api/harness/r1/c1/0")

    assert locked.status_code == 403 and reviewing.status_code == 403
    assert engineering.status_code == 200
