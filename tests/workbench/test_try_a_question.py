"""Try a question within a daily dollar limit, and keep it as a case (decision 0052)."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from casebench.capture.step import Step, StepKind
from casebench.config import CasebenchConfig
from casebench.core.case import Approval
from casebench.runs.log import Result
from casebench.suites.freeze import freeze, load
from casebench.workbench.app import PERSON_HEADER, create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from casebench.workbench.trying import Asked
from tests.corpus.document_api import WORKS
from tests.judge.fake_judge import start_fake_judge
from tests.workbench.agents import SPOT_ANSWER

HOST = "testserver"
AGENTS = Path(__file__).parent / "agents.py"


def as_(name: str) -> dict[str, str]:
    return {PERSON_HEADER: quote(name)}


def corpus(folder: Path) -> Path:
    folder.mkdir()
    for work_id, work in WORKS.items():
        document = {"id": work_id, "jurisdiction": "TR", "text": work["text"]}
        (folder / f"{work_id}.json").write_text(json.dumps(document), encoding="utf-8")
    return folder


def app_for(tmp_path: Path, config: dict[str, Any], asker: Any = None) -> TestClient:
    freeze("labour", [], tmp_path / "suites" / "labour")
    parsed = CasebenchConfig.model_validate(config)
    workspace = Workspace(tmp_path / "runs", [tmp_path / "suites"], None, parsed.agent_models)
    store = Store(f"sqlite:///{tmp_path / 'casebench.db'}")
    app = create_app(workspace, store, [HOST], config=parsed, asker=asker)
    return TestClient(app, base_url=f"http://{HOST}")


def test_spot_check_to_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_fake_judge()
    judge = {
        "provider": "anthropic",
        "model": "judge-model",
        "options": {"base_url": f"http://127.0.0.1:{server.server_port}", "max_tokens": 1024},
        "price": {"input": 3.0, "output": 15.0},
    }
    config = {
        "target": {"type": "python", "entry": f"{AGENTS}:assistant"},
        "judge": judge,
        "corpus": {"connector": "folder", "options": {"path": str(corpus(tmp_path / "docs"))}},
        "agent_models": [
            {"model": "agent-model", "family": "a", "price": {"input": 1, "output": 2}}
        ],
        "workbench": {"try_daily_limit_usd": 5, "second_approval": True},
    }
    app = app_for(tmp_path, config)

    before = app.get("/api/try", headers=as_("Ayşe")).json()
    tried = app.post("/api/try", json={"question": "Is the dismissal valid?"}, headers=as_("Ayşe"))
    server.shutdown()
    saved = app.post(
        "/api/golden/labour",
        json={
            "task": "qa",
            "fields": {
                "question": "Is the dismissal valid?",
                "reference answer": "No: the employer gave no valid reason.",
                "key points": "+5 Says the dismissal is invalid\n-4 Cites a decision not in force",
            },
        },
        headers=as_("Ayşe"),
    )

    assert before["can_ask"] is True and before["remaining"] == 5
    assert before["checks_citations"] is True
    assert tried.status_code == 200, tried.text
    answer = tried.json()
    assert answer["answer"] == SPOT_ANSWER
    labels = {c["citation"]: c["label"] for c in answer["citations"]}
    assert labels["Yargıtay 9. HD, E. 2023/1234 K. 2024/567"] == "verified"
    assert labels["Yargıtay 3. HD, E. 2021/999 K. 2022/1"] == "fabricated"
    # The judge's calls are counted against the day's limit.
    assert answer["judge_cost"] > 0 and answer["cost"] == pytest.approx(answer["judge_cost"])
    assert answer["budget"]["spent_today"] == pytest.approx(answer["cost"])
    # Saved as a case, it joins the suite as a draft awaiting a second editor's approval.
    assert saved.status_code == 200, saved.text
    [case] = load(tmp_path / "suites" / "labour")[1]
    assert (
        case.approval is Approval.DRAFT
        and case.task.inputs["question"] == "Is the dismissal valid?"
    )


class Priced:
    """A target whose every question costs the agent a known amount, and that counts its
    questions."""

    def __init__(self, model: str = "agent-model") -> None:
        self.model = model
        self.asked = 0

    async def ask(self, question: str) -> Asked:
        self.asked += 1
        # 100,000 input and 50,000 output tokens at $2 and $8 per million: $0.60.
        step = Step(kind=StepKind.LLM, model=self.model, input_tokens=100_000, output_tokens=50_000)
        result = Result(case_id="try", output="An answer.", steps=[step])
        return Asked(result=result, citations=[], judge_cost=0.0)


PRICED = {
    "target": {"type": "python", "entry": "x:y"},
    "agent_models": [{"model": "agent-model", "family": "a", "price": {"input": 2, "output": 8}}],
    "workbench": {"try_daily_limit_usd": 1.0},
}


def test_spend_limit_holds(tmp_path: Path):
    target = Priced()
    app = app_for(tmp_path, PRICED, target)

    first = app.post("/api/try", json={"question": "One?"}, headers=as_("Ayşe"))
    second = app.post("/api/try", json={"question": "Two?"}, headers=as_("Can"))
    third = app.post("/api/try", json={"question": "Three?"}, headers=as_("Ayşe"))
    budget = app.get("/api/try", headers=as_("Ayşe")).json()

    assert first.status_code == 200 and first.json()["cost"] == pytest.approx(0.60)
    # Under the limit before it was sent, so it was sent; now the day's spend is over it.
    assert second.status_code == 200
    assert third.status_code == 422
    assert "today's limit of $1.00 is spent" in third.json()["detail"]
    assert target.asked == 2
    assert budget["can_ask"] is False and budget["remaining"] == 0
    assert budget["spent_today"] == pytest.approx(1.20)


@pytest.mark.parametrize(
    ("config", "why"),
    [
        ({**PRICED, "workbench": None}, "no daily limit is set"),
        ({**PRICED, "agent_models": [{"model": "agent-model", "family": "a"}]}, "has no price"),
        ({**PRICED, "target": None}, "no target"),
    ],
)
def test_nothing_is_sent_without_a_measurable_limit(tmp_path: Path, config: dict, why: str):
    target = Priced()
    app = app_for(tmp_path, config, target)

    refused = app.post("/api/try", json={"question": "Is it valid?"}, headers=as_("Ayşe"))

    assert refused.status_code == 422 and why in refused.json()["detail"]
    assert target.asked == 0


def test_a_model_without_a_price_stops_further_questions(tmp_path: Path):
    target = Priced(model="surprise-model")
    app = app_for(tmp_path, PRICED, target)

    first = app.post("/api/try", json={"question": "One?"}, headers=as_("Ayşe"))
    second = app.post("/api/try", json={"question": "Two?"}, headers=as_("Ayşe"))

    assert first.status_code == 200 and first.json()["unpriced"] == ["surprise-model"]
    assert second.status_code == 422 and "surprise-model" in second.json()["detail"]
    assert target.asked == 1
