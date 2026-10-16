# SPDX-License-Identifier: Elastic-2.0
"""An engineer pushes runs and suites to the team server, invites a lawyer, and pulls the
lawyers' decisions back; nothing the line keeps back crosses it, and the server never scores
(decision 0059)."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from casebench.capture.step import Step, StepKind, ToolCall
from casebench.cli import main
from casebench.cloud.client import Cloud, CloudError
from casebench.cloud.sync import pull, push
from casebench.core.case import Approval
from casebench.report.calibration import lawyers_win, read_reviews
from casebench.runs.log import RunLog
from casebench.suites.freeze import freeze, load
from casebench.workbench.items import answer_key, draft_key
from casebench.workbench.sources import Workspace
from casebench_ee.mail import Outbox
from casebench_ee.server import Server, build
from team_tests.helpers import PUBLIC, browser, signed_in
from tests.report.suites import frozen, mixed
from tests.workbench.test_review_queue import TEXT, court_draft, reviewed_case, scored_run

AGENTS = Path(__file__).parents[2] / "tests" / "report" / "agents.py"
SECRET_ARGUMENT = "client Ayşe Yılmaz, file 2024/118, fired by WhatsApp"
KEY_VALUE = "sk-ant-api03-not-a-real-key-but-shaped-like-one"


def team_server(database: str, root: Path, outbox: Outbox | None = None) -> Server:
    return build(database, PUBLIC, root / "runs", [root / "suites"], mailer=outbox or Outbox())


def engineer_cloud(server: Server) -> Cloud:
    server.team.add("selin@firm.example", "Selin Kaya", "admin", "setup")
    _, token = server.team.new_key("Selin's laptop", "engineer", "Selin Kaya")
    http = TestClient(server.app, base_url=PUBLIC, headers={"Authorization": f"Bearer {token}"})
    return Cloud(http)


def laptop(root: Path) -> Workspace:
    """A suite with an approved answer case and a court draft, and a scored run whose answer
    took a step with arguments, beside the judge's kept replies and the corpus."""
    suite = freeze("suite", [reviewed_case(), court_draft()], root / "suites" / "suite")
    log = scored_run(root / "runs", reviewed_case(), suite.content_hash)
    step = Step(
        kind=StepKind.TOOL,
        name="search",
        arguments={"query": SECRET_ARGUMENT},
        requested_tools=[ToolCall(id="t1", name="search", arguments={"q": SECRET_ARGUMENT})],
        started=1.0,
        ended=1.5,
        duration_ms=500,
        doc_ids_out=["tr-1"],
    )
    results = log.results()
    (log.folder / "results.jsonl").write_text(
        "".join(r.model_copy(update={"steps": [step]}).model_dump_json() + "\n" for r in results),
        encoding="utf-8",
    )
    (log.folder / "judge.jsonl").write_text(json.dumps({"prompt": TEXT}) + "\n", encoding="utf-8")
    (log.folder / "notes.txt").write_text(KEY_VALUE, encoding="utf-8")
    (root / "decisions").mkdir()
    (root / "decisions" / "tr-1.json").write_text(json.dumps({"text": TEXT}), encoding="utf-8")
    return Workspace(root / "runs", [root / "suites"])


def everything_on(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*") if p.is_file())


def test_from_laptop_to_the_cloud(database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY_VALUE)
    outbox = Outbox()
    server = team_server(database, tmp_path / "server", outbox)
    cloud = engineer_cloud(server)
    workspace = laptop(tmp_path / "laptop")

    pushed = push(cloud, workspace, workspace.runs(), traces=False)
    invited = cloud.invite("ayse@firm.example", "Ayşe Yılmaz", "reviewer")
    [(to, _, text)] = outbox.sent
    link = re.search(r"http\S+", text)
    assert link is not None
    lawyer = browser(server)
    lawyer.get(link.group(0).removeprefix(PUBLIC), follow_redirects=False)
    queue = lawyer.get("/api/queue").json()["items"]
    on_server = everything_on(tmp_path / "server")

    assert pushed.runs == ["r1"] and pushed.suites == ["suite"]
    assert (invited["waiting"], invited["minutes"]) == (1, 2)
    assert to == "ayse@firm.example"
    assert "1 item wait for you in the queue, about 2 minutes of work" in text
    assert [i["key"] for i in queue] == [answer_key("r1", "answer-1", 0)]
    # What stays on the laptop: the judge's replies, other files, the corpus, full decision
    # texts, tool arguments and keys.
    run = tmp_path / "server" / "runs" / "r1"
    assert sorted(p.name for p in run.iterdir() if p.is_file()) == ["results.jsonl", "run.json"]
    assert not (run / "judge.jsonl").exists() and not (run / "notes.txt").exists()
    assert TEXT not in on_server
    assert SECRET_ARGUMENT not in on_server
    assert KEY_VALUE not in on_server
    assert not list((tmp_path / "server").rglob("tr-1.json"))
    # An engineer's key invites reviewers, not engineers.
    with pytest.raises(CloudError, match="engineer role cannot administer"):
        cloud.invite("emre@firm.example", "Emre", "engineer")


def test_traces_only_on_request(database: str, tmp_path: Path):
    server = team_server(database, tmp_path / "server")
    cloud = engineer_cloud(server)
    workspace = laptop(tmp_path / "laptop")
    sent = tmp_path / "server" / "runs" / "r1" / "results.jsonl"

    push(cloud, workspace, workspace.runs(), traces=False)
    [without] = [json.loads(line) for line in sent.read_text(encoding="utf-8").splitlines()]
    push(cloud, workspace, workspace.runs(), traces=True)
    [traced] = [json.loads(line) for line in sent.read_text(encoding="utf-8").splitlines()]

    assert without["steps"] == []
    [step] = traced["steps"]
    assert (step["kind"], step["name"], step["duration_ms"], step["doc_ids_out"]) == (
        "tool",
        "search",
        500,
        ["tr-1"],
    )
    assert "arguments" not in step and step["requested_tools"] == [{"id": "t1", "name": "search"}]
    assert SECRET_ARGUMENT not in sent.read_text(encoding="utf-8")


def test_push_is_idempotent(database: str, tmp_path: Path):
    server = team_server(database, tmp_path / "server")
    cloud = engineer_cloud(server)
    workspace = laptop(tmp_path / "laptop")
    reviewer = signed_in(server, "ayse@firm.example", "Ayşe Yılmaz", "reviewer")

    first = push(cloud, workspace, workspace.runs(), traces=False)
    key = answer_key("r1", "answer-1", 0)
    reviewer.post(f"/api/items/{key}/reserve")
    reviewer.post(
        f"/api/items/{key}/finish",
        json={
            "verdicts": [
                {"criterion_id": "c-statute-1", "verdict": "fail", "note": "wrong article"}
            ]
        },
    )
    second = push(cloud, workspace, workspace.runs(), traces=False)
    runs = browser(server)
    runs.cookies = reviewer.cookies

    assert first.runs == ["r1"] and second.runs == [] and second.unchanged == 2
    assert [r["run_id"] for r in reviewer.get("/api/runs").json()] == ["r1"]
    # The lawyer's verdict given on the server survives the second push.
    reviews = read_reviews(tmp_path / "server" / "runs" / "r1")
    assert [(r.verdict, r.by) for r in reviews] == [("fail", "Ayşe Yılmaz")]


def test_approvals_come_back_to_ci(database: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Forty court drafts approved and three verdicts overruled on the server come back with
    one pull, and the next run and the gate count only what lawyers approved."""
    project = tmp_path / "laptop"
    project.mkdir()
    monkeypatch.chdir(project)
    frozen(mixed(40), project / "suite")
    answers = [reviewed_case().model_copy(update={"id": f"answer-{n}"}) for n in range(1, 4)]
    answer_suite = freeze("answers", answers, project / "answers")
    runs = project / "runs"

    def run(run_id: str):
        return CliRunner().invoke(
            main,
            ["run", "--suite", str(project / "suite"), "--config", str(project / "none.yaml"),
             "--python", f"{AGENTS}:from_facts", "--runs-dir", str(runs), "--run-id", run_id],
        )  # fmt: skip

    assert run("baseline").exit_code == 0 and run("new").exit_code == 0
    answered = scored_run(runs, answers[0], answer_suite.content_hash)
    for case in answers[1:]:
        extra = scored_run(tmp_path / "scratch" / case.id, case, answer_suite.content_hash)
        answered.append(extra.results()[0].model_copy(update={"case_id": case.id}))
        scores = RunLog.read_scores(extra.score_sets()[-1])
        sets = answered.score_sets()
        combined = sets[-1].read_text(encoding="utf-8") + "".join(
            s.model_copy(update={"case_id": case.id}).model_dump_json() + "\n" for s in scores
        )
        sets[-1].write_text(combined, encoding="utf-8")
    before_gate = CliRunner().invoke(main, ["gate", str(runs / "baseline"), str(runs / "new")])

    server = team_server(database, tmp_path / "server")
    cloud = engineer_cloud(server)
    workspace = Workspace(runs, [project])
    push(cloud, workspace, workspace.runs(), traces=False)
    editor = signed_in(server, "deniz@firm.example", "Deniz", "editor")
    for n in range(40):
        key = draft_key("outcomes", f"case-{n:03d}")
        editor.post(f"/api/items/{key}/reserve")
        done = editor.post(
            f"/api/items/{key}/finish",
            json={"facts": [{"fact_id": "outcome", "decision": "approve"}]},
        )
        assert done.status_code == 200, done.text
    reviewer = signed_in(server, "ayse@firm.example", "Ayşe", "reviewer")
    for case in answers:
        key = answer_key("r1", case.id, 0)
        reviewer.post(f"/api/items/{key}/reserve")
        overruled = reviewer.post(
            f"/api/items/{key}/finish",
            json={"verdicts": [{"criterion_id": "c-statute-1", "verdict": "fail",
                                "note": "m. 18 is cited for reinstatement"}]},
        )  # fmt: skip
        assert overruled.status_code == 200, overruled.text
    # Pushing the old suite again is refused until the lawyers' changes are pulled.
    with pytest.raises(CloudError, match="run casebench pull"):
        push(cloud, workspace, workspace.runs(), traces=False)

    pulled = pull(cloud, workspace)
    _, cases = load(project / "suite")
    shown = lawyers_win(
        RunLog.read_scores(answered.score_sets()[-1]), read_reviews(answered.folder)
    )
    assert run("baseline-2").exit_code == 0 and run("new-2").exit_code == 0
    after_gate = CliRunner().invoke(main, ["gate", str(runs / "baseline-2"), str(runs / "new-2")])

    assert "40 draft cases were left out" in before_gate.output
    assert sorted(pulled.suites) == ["outcomes"] and pulled.reviews == 3
    assert sum(c.approval is Approval.APPROVED for c in cases) == 40
    overruled_verdicts = [v for s in shown if s.metric == "criteria" for v in s.criteria]
    assert len(overruled_verdicts) == 3
    assert all(not v.met and v.reviewed_by == "Ayşe" for v in overruled_verdicts)
    assert after_gate.exit_code == 0, after_gate.output
    assert "draft cases were left out" not in after_gate.output
    assert push(cloud, workspace, workspace.runs(), traces=False).runs


def test_the_cloud_never_grades(database: str, tmp_path: Path):
    server = team_server(database, tmp_path / "server")
    cloud = engineer_cloud(server)
    workspace = laptop(tmp_path / "laptop")
    reviewer = signed_in(server, "ayse@firm.example", "Ayşe", "reviewer")

    push(cloud, workspace, workspace.runs(), traces=False)
    key = answer_key("r1", "answer-1", 0)
    reviewer.post(f"/api/items/{key}/reserve")
    reviewer.post(
        f"/api/items/{key}/finish",
        json={"verdicts": [{"criterion_id": "c-statute-1", "verdict": "fail", "note": "no"}]},
    )
    [local] = workspace.runs()[0].score_sets()
    [stored] = (tmp_path / "server" / "runs" / "r1" / "scores").iterdir()
    paths: list[Any] = [getattr(route, "path", "") for route in server.app.routes]

    # The score set is the runner's, byte for byte, even after a lawyer's verdict.
    assert stored.read_bytes() == local.read_bytes()
    assert not [p for p in paths if re.search(r"score|grade|judge|rerun", p)]


def test_a_push_never_leaves_the_servers_folders(database: str, tmp_path: Path):
    server = team_server(database, tmp_path / "server")
    cloud = engineer_cloud(server)
    info = {"run_id": "..", "suite_id": "s", "suite_hash": "h", "target": "t"}
    tries = [
        ("..", {"run.json": json.dumps(info)}),
        ("r1", {"scores/../../escape.jsonl": "{}"}),
        ("r1", {"judge.jsonl": "{}"}),
    ]

    for run_id, sent in tries:
        with pytest.raises(CloudError):
            cloud.push_run(run_id, sent)

    assert not list(tmp_path.rglob("escape.jsonl"))
    assert not (tmp_path / "server" / "runs" / "r1").exists()
