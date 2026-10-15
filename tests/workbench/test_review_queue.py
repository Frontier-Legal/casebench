"""The review queue: a lawyer's first session in the workbench (decision 0050). The keyboard
scenario is tested with the web app, in workbench/src/review.test.tsx."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from casebench.capture.step import Step, StepKind
from casebench.cli import main
from casebench.core.case import (
    Approval,
    Case,
    Criterion,
    Evidence,
    Fact,
    Provenance,
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
from casebench.corpus.binding import CorpusConfig
from casebench.corpus.corpora import Corpora
from casebench.judge.config import Price
from casebench.judge.families import AgentModel
from casebench.report.calibration import lawyers_win, read_reviews
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.producer import Producer
from casebench.suites.freeze import freeze, load
from casebench.workbench.app import PERSON_HEADER, create_app
from casebench.workbench.items import answer_key, draft_key
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store

HOST = "testserver"
DECISION = "corpus:tr-1"
TEXT = (
    "Yargıtay 9. Hukuk Dairesi. Davacı işçi, iş sözleşmesinin geçerli sebep olmadan "
    "feshedildiğini ileri sürmüştür. 4857 sayılı İş Kanunu m. 18 uyarınca fesih geçerli sebebe "
    "dayanmalıdır. 4857 sayılı İş Kanunu m. 21 işe iadenin sonuçlarını düzenler. Daire, "
    "Yargıtay 9. HD E. 2019/1 K. 2020/2 kararına atıfla yerel mahkeme kararını onamıştır."
)
ANSWER = (
    "The dismissal is invalid under İş Kanunu m. 18, which requires a valid reason "
    "(Yargıtay 9. HD, E. 2023/1234 K. 2024/567). Reinstatement follows İş Kanunu m. 21. "
    "See also Yargıtay 22. HD, E. 2022/77 K. 2023/90 and Yargıtay 3. HD, E. 2021/999 K. 2022/1."
)
AGENT = Path(__file__).parent / "agents.py"


def passage(quoted: str) -> Evidence:
    start = TEXT.index(quoted)
    return Evidence(doc=DECISION, span=(start, start + len(quoted)), quote=quoted)


def court_draft() -> Case:
    """An outcome, two statutes and one precedent, each with its passage in the decision."""
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
            document_id="corpus:law-18",
        ),
        Fact(
            id="statute-2",
            kind="statute",
            value="4857 sayılı İş Kanunu m. 21",
            evidence=passage("4857 sayılı İş Kanunu m. 21"),
        ),
        Fact(
            id="precedent-1",
            kind="precedent",
            value="Yargıtay 9. HD E. 2019/1 K. 2020/2",
            evidence=passage("Yargıtay 9. HD E. 2019/1 K. 2020/2"),
        ),
    ]
    return Case(
        id="draft-1",
        task=Task.model_validate(
            {"type": "outcome", "question": "How did the court rule?", "facts": "Davacı işçi..."}
        ),
        reference=Reference(source=ReferenceSource.COURT, facts=facts),
        metrics=["outcome"],
        provenance=Provenance(builder="court", source_decision_id=DECISION),
    )


def reviewed_case() -> Case:
    statute = Fact(
        id="statute-1",
        kind="statute",
        value="4857 sayılı İş Kanunu m. 18",
        evidence=passage("4857 sayılı İş Kanunu m. 18"),
    )
    return Case(
        id="answer-1",
        task=Task.model_validate({"type": "qa", "question": "Is the dismissal valid?"}),
        reference=Reference(
            source=ReferenceSource.COURT,
            facts=[statute],
            criteria=[
                Criterion(
                    id="c-statute-1",
                    text="Passes if the answer relies on İş Kanunu m. 18. Fails if it does not.",
                    weight=1,
                    derived_from=["statute-1"],
                )
            ],
        ),
        metrics=["criteria", "citation_integrity"],
        approval=Approval.APPROVED,
    )


def scored_run(runs: Path, case: Case, suite_hash: str) -> RunLog:
    """A run whose judge passed the criterion and whose four citations the corpus checked."""
    log = RunLog.create(
        runs / "r1", RunInfo(run_id="r1", suite_id="suite", suite_hash=suite_hash, target="agent")
    )
    step = Step(kind=StepKind.LLM, model="agent-model", input_tokens=812, output_tokens=95)
    log.append(Result(case_id=case.id, output=ANSWER, latency_ms=1840.0, steps=[step]))
    common: dict[str, Any] = {
        "case_id": case.id,
        "kind": ScoreKind.LLM,
        "direction": Direction.HIGHER,
        "metric_version": "1",
        "task_type": "qa",
        "reference_source": ReferenceSource.COURT,
        "approval": Approval.APPROVED,
    }
    met = CriterionVerdict(
        criterion_id="c-statute-1", weight=1, met=True, quote="İş Kanunu m. 18", kind="statute"
    )
    checks = [
        CitationCheck(
            citation="Yargıtay 9. HD, E. 2023/1234 K. 2024/567",
            claim="a valid reason is needed",
            label=CitationLabel.VERIFIED,
            document_id=DECISION,
            quote="fesih geçerli sebebe dayanmalıdır",
        ),
        CitationCheck(
            citation="İş Kanunu m. 21",
            claim="reinstatement",
            label=CitationLabel.VERIFIED,
            document_id=DECISION,
            quote="işe iadenin sonuçlarını düzenler",
        ),
        CitationCheck(
            citation="Yargıtay 22. HD, E. 2022/77 K. 2023/90",
            claim="dismissal is invalid",
            label=CitationLabel.MISGROUNDED,
            document_id=DECISION,
            reason="the passage says something else",
        ),
        CitationCheck(
            citation="Yargıtay 3. HD, E. 2021/999 K. 2022/1",
            claim="see also",
            label=CitationLabel.FABRICATED,
        ),
    ]
    scores = [
        Score(metric="criteria", value=1.0, label="all criteria passed", criteria=[met], **common),
        Score(
            metric="citation_integrity", value=0.5, label="2 verified", citations=checks, **common
        ),
    ]
    log.write_score_set(scores, Producer(metrics={}))
    return log


def write_corpus(folder: Path) -> Corpora:
    folder.mkdir()
    record = {
        "id": "tr-1",
        "jurisdiction": "TR",
        "court": "Yargıtay 9. HD",
        "date": "2020-03-01",
        "text": TEXT,
    }
    (folder / "tr-1.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return Corpora(
        {"corpus": CorpusConfig(connector="folder", options={"path": str(folder)})},
        cache_root=folder.parent / "cache",
    )


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Any]:
    suite = freeze("suite", [reviewed_case()], tmp_path / "suites" / "suite")
    freeze("drafts", [court_draft()], tmp_path / "suites" / "drafts")
    log = scored_run(tmp_path / "runs", reviewed_case(), suite.content_hash)
    priced = AgentModel(model="agent-model", family="agent", price=Price(input=3.0, output=15.0))
    workspace = Workspace(
        tmp_path / "runs", [tmp_path / "suites"], write_corpus(tmp_path / "decisions"), [priced]
    )
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    return {"tmp": tmp_path, "workspace": workspace, "store": store, "log": log}


def client(project: dict[str, Any], role: str | None = None) -> TestClient:
    app = create_app(project["workspace"], project["store"], [HOST], role)
    return TestClient(app, base_url=f"http://{HOST}")


def as_(name: str) -> dict[str, str]:
    return {PERSON_HEADER: quote(name)}


ANSWER_KEY = answer_key("r1", "answer-1", 0)
DRAFT_KEY = draft_key("drafts", "draft-1")


def test_overrule_the_judge(project: dict[str, Any]):
    app = client(project)
    app.put("/api/me", json={"name": "Ayşe", "view": "review"})
    queued = app.get("/api/queue", headers=as_("Ayşe")).json()["items"]
    item = app.get(f"/api/items/{ANSWER_KEY}", headers=as_("Ayşe")).json()
    url = f"/api/items/{ANSWER_KEY}/finish"
    fail = {"criterion_id": "c-statute-1", "verdict": "fail"}

    unexplained = app.post(url, json={"verdicts": [fail]}, headers=as_("Ayşe"))
    note = "m. 18 is cited for reinstatement, which m. 21 governs"
    overruled = app.post(url, json={"verdicts": [{**fail, "note": note}]}, headers=as_("Ayşe"))
    after = app.get("/api/queue", headers=as_("Ayşe")).json()["items"]

    assert [i["key"] for i in queued] == [ANSWER_KEY, DRAFT_KEY]
    [criterion] = item["criteria"]
    assert criterion["judge"] == "pass" and criterion["lawyer"] is None
    assert unexplained.status_code == 422
    assert "add a note" in unexplained.json()["detail"]
    assert overruled.status_code == 200, overruled.text
    assert "overruling the judge" in overruled.json()["message"]
    assert [i["key"] for i in after] == [DRAFT_KEY]
    # The verdict replaces the judge's in the scores, which keep the judge's beside it.
    log: RunLog = project["log"]
    [review] = read_reviews(log.folder)
    assert (review.verdict, review.judge, review.by, review.note) == ("fail", "pass", "Ayşe", note)
    scores = lawyers_win(RunLog.read_scores(log.score_sets()[-1]), read_reviews(log.folder))
    [criteria] = [s for s in scores if s.metric == "criteria"]
    assert criteria.value == 0.0 and criteria.criteria[0].reviewed_by == "Ayşe"
    assert criteria.criteria[0].judge_met is True
    events = [(e.action, e.subject, e.before, e.after, e.reason) for e in project["store"].events()]
    assert events[0] == ("verdict", "c-statute-1", "pass", "fail", note)


def test_approve_a_court_draft_with_evidence_in_view(project: dict[str, Any]):
    tmp: Path = project["tmp"]
    # Before anyone approves it, the draft can be run, and its scores are unreviewed.
    ran = CliRunner().invoke(
        main,
        ["run", "--suite", str(tmp / "suites" / "drafts"), "--config", str(tmp / "none.yaml"),
         "--python", f"{AGENT}:upheld", "--runs-dir", str(tmp / "draft-runs"), "--run-id", "d",
         "--no-capture"],
    )  # fmt: skip
    assert ran.exit_code == 0, ran.output
    report = json.loads((tmp / "draft-runs" / "d" / "report.json").read_text(encoding="utf-8"))
    rows = [(t["metric"], r["approval"]) for t in report["tables"] for r in t["rows"]]
    assert ("outcome", "unreviewed") in rows

    app = client(project)
    app.put("/api/me", json={"name": "Ayşe", "view": "review"})
    item = app.get(f"/api/items/{DRAFT_KEY}", headers=as_("Ayşe")).json()
    url = f"/api/items/{DRAFT_KEY}/finish"
    decided = [
        {"fact_id": "outcome-1", "decision": "approve"},
        {"fact_id": "statute-1", "decision": "approve"},
        {"fact_id": "statute-2", "decision": "edit", "value": "4857 sayılı İş Kanunu m. 21/1"},
        {"fact_id": "precedent-1", "decision": "reject"},
    ]
    unexplained = app.post(url, json={"facts": decided}, headers=as_("Ayşe"))
    decided[2]["reason"] = "the court relies on the first paragraph only"
    approved = app.post(url, json={"facts": decided}, headers=as_("Ayşe"))

    # Each fact is shown beside its passage, highlighted in the decision's text.
    assert item["decision"]["text"] == TEXT and item["decision"]["court"] == "Yargıtay 9. HD"
    for fact in item["facts"]:
        mark = fact["highlight"]
        assert TEXT[mark["start"] : mark["end"]] == fact["quote"]
    assert unexplained.status_code == 422 and "needs a reason" in unexplained.json()["detail"]
    assert approved.status_code == 200, approved.text
    manifest, cases = load(tmp / "suites" / "drafts")
    [case] = [c for c in cases if c.id == "draft-1"]
    assert case.approval is Approval.APPROVED and case.reference.author == "Ayşe"
    facts = {f.id: f for f in case.reference.facts}
    assert set(facts) == {"outcome-1", "statute-1", "statute-2"}
    assert facts["statute-2"].value == "4857 sayılı İş Kanunu m. 21/1"
    assert facts["statute-2"].evidence.note == (
        "edited by Ayşe: the court relies on the first paragraph only"
    )
    assert facts["statute-1"].document_id == "corpus:law-18"
    assert manifest.content_hash in approved.json()["message"]
    actions = [(e.action, e.subject) for e in project["store"].events(DRAFT_KEY)]
    assert actions == [
        ("approve", "outcome-1"),
        ("approve", "statute-1"),
        ("edit", "statute-2"),
        ("reject", "precedent-1"),
        ("finished", "draft-1"),
    ]


def test_citations_coloured_by_what_the_corpus_says(project: dict[str, Any]):
    app = client(project)
    app.put("/api/me", json={"name": "Ayşe", "view": "review"})

    item = app.get(f"/api/items/{ANSWER_KEY}", headers=as_("Ayşe")).json()
    first = item["citations"][0]
    opened = app.get(
        f"/api/documents/{first['document_id']}",
        params={"quote": first["quote"]},
        headers=as_("Ayşe"),
    ).json()

    labels = [c["label"] for c in item["citations"]]
    assert labels == ["verified", "verified", "misgrounded", "fabricated"]
    assert opened["text"] == TEXT
    mark = opened["highlight"]
    assert TEXT[mark["start"] : mark["end"]] == "fesih geçerli sebebe dayanmalıdır"


ENGINEERING = ("steps", "input_tokens", "output_tokens", "latency_ms", "raw")


def keys_in(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys_in(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys_in(v)}
    return set()


def test_no_engineering_on_screen(project: dict[str, Any]):
    engineer = client(project)
    engineer.put("/api/me", json={"name": "Emre", "view": "engineering"})
    reviewer = client(project, role="reviewer")

    built = engineer.get(f"/api/items/{ANSWER_KEY}", headers=as_("Emre")).json()
    # Emre chose the engineering view; the app with the reviewer role serves the review view.
    asked = reviewer.get("/api/me", headers=as_("Emre")).json()
    answer = reviewer.get(f"/api/items/{ANSWER_KEY}", headers=as_("Emre")).json()
    draft = reviewer.get(f"/api/items/{DRAFT_KEY}", headers=as_("Emre")).json()
    switched = reviewer.put("/api/me", json={"name": "Can", "view": "engineering"}).json()

    assert built["engineering"]["input_tokens"] == 812
    # What the answer cost the agent, at the price casebench.yaml gives its model (0051).
    assert built["engineering"]["cost"] == pytest.approx((812 * 3.0 + 95 * 15.0) / 1_000_000)
    assert built["engineering"]["steps"][0]["model"] == "agent-model"
    # No response carries a span, a token count or a raw record, and no one can switch.
    assert asked["view"] == "review" and asked["role_locked"] is True
    assert switched["view"] == "review"
    for shown in (answer, draft):
        assert shown["engineering"] is None
        assert not keys_in(shown) & set(ENGINEERING)
    assert "812" not in json.dumps(answer)


def test_an_open_item_is_held_for_its_reader(project: dict[str, Any]):
    app = client(project)
    app.post(f"/api/items/{ANSWER_KEY}/reserve", headers=as_("Ayşe"))
    app.put(
        f"/api/items/{ANSWER_KEY}/draft",
        json={"payload": {"c-statute-1": {"verdict": "fail"}}},
        headers=as_("Ayşe"),
    )

    other = app.post(f"/api/items/{ANSWER_KEY}/reserve", headers=as_("Can"))
    theirs = app.get("/api/queue", headers=as_("Can")).json()["items"]
    mine = app.get(f"/api/items/{ANSWER_KEY}", headers=as_("Ayşe")).json()

    assert other.status_code == 409 and "Ayşe is working on this item" in other.json()["detail"]
    assert ANSWER_KEY not in [i["key"] for i in theirs]
    assert mine["draft"] == {"c-statute-1": {"verdict": "fail"}}


def test_only_this_machine_reaches_it(project: dict[str, Any]):
    app = client(project)

    rebound = app.get("/api/queue", headers={**as_("Ayşe"), "host": "attacker.example"})
    forged = app.post(
        f"/api/items/{ANSWER_KEY}/reserve",
        headers={**as_("Ayşe"), "origin": "http://attacker.example"},
    )
    nameless = app.get("/api/queue")

    assert rebound.status_code == 403
    assert forged.status_code == 403
    assert nameless.status_code == 401


def test_the_app_serves_only_its_own_files(project: dict[str, Any]):
    built = project["tmp"] / "static"
    built.mkdir()
    (built / "index.html").write_text("<p>the app</p>", encoding="utf-8")
    (built / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    app = TestClient(
        create_app(project["workspace"], project["store"], [HOST], static=built),
        base_url=f"http://{HOST}",
    )

    icon = app.get("/favicon.svg")
    deep = app.get("/review/answer")
    escaped = [app.get(path) for path in ("/..%2Fcasebench.db", "/%2e%2e/casebench.db")]

    assert icon.text == "<svg></svg>"
    assert deep.text == "<p>the app</p>"
    assert all(r.text == "<p>the app</p>" for r in escaped)
