"""The judge grades only against the case's evidence: a verdict quotes the answer and names its
evidence, a case without facts is unevidenced, a judge of the agent's family is warned about,
and lawyers' verdicts calibrate the judge (decision 0047)."""

import inspect
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

import casebench
from casebench.cases.build import Written, lawyer_case
from casebench.cli import main
from casebench.core.case import (
    Case,
    Criterion,
    Evidence,
    Fact,
    Reference,
    ReferenceSource,
    Task,
)
from casebench.core.score import CriterionVerdict, ScoreKind
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.judge.families import AgentModel, family_warnings
from casebench.metrics.builtin.criteria import JudgeGrader
from casebench.metrics.criteria import UNQUOTED, WeightedCriteria
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.providers.interface import HttpRequest
from casebench.runs.log import Result, RunLog
from tests.judge.fake_judge import start_fake_judge
from tests.report.suites import criteria_case, frozen

AGENTS = Path(__file__).parents[1] / "report" / "agents.py"
PASSAGE = "Daire, yerel mahkeme kararını onamıştır."
ANSWER = "The decision is upheld: the chamber affirmed the lower court."


@pytest.fixture
def port(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_fake_judge()
    yield server.server_port
    server.shutdown()


def judge_block(port: int, family: str = "claude") -> dict[str, Any]:
    options = {"base_url": f"http://127.0.0.1:{port}", "max_tokens": 1024, "family": family}
    return {"provider": "anthropic", "model": "judge-model", "options": options}


def run(tmp_path: Path, cases: list[Case], **config: Any):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    suite = frozen(cases, tmp_path / "suite")
    return CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(suite),
            "--config",
            str(tmp_path / "casebench.yaml"),
            "--python",
            f"{AGENTS}:upheld",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--run-id",
            "r",
        ],
    )


def report(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "runs" / "r" / "report.json").read_text(encoding="utf-8"))


def evidenced_case() -> Case:
    court = Fact(
        id="f1", kind="outcome", value="upheld", evidence=Evidence(doc="tr:1", quote=PASSAGE)
    )
    lawyer = Fact(
        id="f2",
        kind="answer",
        value="The appeal fails.",
        evidence=Evidence(doc="reviewer", note="written by Ayşe"),
    )
    return Case(
        id="c1",
        task=Task.model_validate({"type": "qa", "question": "How did the court rule?"}),
        reference=Reference(
            source=ReferenceSource.COURT,
            facts=[court, lawyer],
            criteria=[
                Criterion(id="c-f1", text="Says upheld", weight=1, derived_from=["f1"]),
                Criterion(id="c-f2", text="Says the appeal fails", weight=1, derived_from=["f2"]),
            ],
        ),
        metrics=["criteria"],
    )


class Asked:
    """A judge that finds both criteria met, quoting the answer for one and inventing the
    other's quote, and keeps what it was asked."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def ask(self, system: str, user: str) -> Any:
        self.prompts.append(user)
        return [
            {"id": "c-f1", "met": True, "quote": "the chamber affirmed\nthe lower court"},
            {"id": "c-f2", "met": True, "quote": "The appeal fails."},
        ]


def test_a_verdict_quotes_its_evidence():
    case, judge = evidenced_case(), Asked()

    verdict = WeightedCriteria(JudgeGrader(judge)).judge(  # type: ignore[arg-type]
        case, Result(case_id=case.id, output=ANSWER)
    )

    court, lawyer = verdict.criteria
    # The quote is in the answer, line break aside, so the verdict stands on it.
    assert court.met and court.quote == "the chamber affirmed\nthe lower court"
    assert court.kind == "outcome" and court.evidence == [PASSAGE]
    # The answer never says this, so the judge's "met" does not count.
    assert not lawyer.met and lawyer.quote is None and lawyer.note == UNQUOTED
    assert lawyer.evidence == ["The appeal fails. (written by Ayşe)"]
    # The judge was given the same evidence: the court's passage and the lawyer's note.
    assert PASSAGE in judge.prompts[0] and "written by Ayşe" in judge.prompts[0]


def test_no_rubric_from_nowhere(tmp_path: Path, port: int):
    bare = lawyer_case("bare-1", Written(question="How?", facts="None given."), "Ayşe", None)
    assert bare.reference.criteria == []

    ran = run(
        tmp_path,
        [bare, criteria_case(2, {"Mentions upheld": 1})],
        judge=judge_block(port),
    )

    assert ran.exit_code == 0, ran.output
    assert "unevidenced: 1 cases have no evidenced fact" in ran.output
    saved = report(tmp_path)
    assert saved["unevidenced"] == ["bare-1"]
    assert saved["scoring_errors"] == []
    assert [s["case_id"] for s in saved["scores"]] == ["case-002"]


def test_same_family_warning(tmp_path: Path, port: int):
    cases = [criteria_case(1, {"Mentions upheld": 1})]
    agent = [{"model": "agent-model", "family": "claude"}]

    same = run(tmp_path / "same", cases, judge=judge_block(port), agent_models=agent)
    other = run(tmp_path / "other", cases, judge=judge_block(port, "qwen"), agent_models=agent)

    assert same.exit_code == 0, same.output
    warned = "the judge anthropic/judge-model is of the claude family, as the agent's agent-model"
    assert warned in same.stderr
    assert any(warned in w for w in report(tmp_path / "same")["warnings"])
    assert other.exit_code == 0, other.output
    assert report(tmp_path / "other")["warnings"] == []
    # A model the agent called that the list leaves out is named.
    listed = [AgentModel(model="agent-model", family="claude")]
    [unlisted] = family_warnings([("j", "qwen")], listed, {"agent-model", "other-model"})
    assert "the agent called other-model" in unlisted


def test_overrule_becomes_calibration(tmp_path: Path, port: int):
    cases = [criteria_case(n, {"Mentions upheld": 1}) for n in (1, 2)]
    assert run(tmp_path, cases, judge=judge_block(port)).exit_code == 0
    folder = str(tmp_path / "runs" / "r")

    def review(*args: str):
        return CliRunner().invoke(main, ["review", "criterion", folder, "--by", "Ayşe", *args])

    unexplained = review("--case", "case-001", "--criterion", "c1", "--verdict", "fail")
    overruled = review(
        "--case", "case-001", "--criterion", "c1", "--verdict", "fail",
        "--note", "it names the outcome but not the chamber's reason",
    )  # fmt: skip
    agreed = review("--case", "case-002", "--criterion", "c1", "--verdict", "pass")
    shown = CliRunner().invoke(main, ["report", folder])
    again = run(tmp_path, cases, judge=judge_block(port))

    assert unexplained.exit_code != 0
    assert "overruling it needs --note" in unexplained.output
    assert overruled.exit_code == 0, overruled.output
    assert "overrules the judge (pass)" in overruled.output
    assert agreed.exit_code == 0, agreed.output
    assert "judge vs lawyers · outcome: 1 of 2 agreed, 1 overruled" in shown.output
    assert again.exit_code == 0, again.output
    saved = report(tmp_path)
    assert saved["calibration"] == [{"kind": "outcome", "labelled": 2, "agreed": 1, "overruled": 1}]
    # The lawyer's verdict replaces the judge's in the report's scores; the judge's is kept.
    [overruled_score] = [s for s in saved["scores"] if s["case_id"] == "case-001"]
    [verdict] = overruled_score["criteria"]
    assert overruled_score["value"] == 0.0 and not verdict["met"]
    assert verdict["reviewed_by"] == "Ayşe" and verdict["judge_met"] is True
    score_set = RunLog.read_scores(RunLog(tmp_path / "runs" / "r").score_sets()[-1])
    assert [s.value for s in score_set if s.case_id == "case-001"] == [1.0]


def test_one_provider_interface():
    providers = [item.name for item in registry.available(kind_named("provider"))]
    root = Path(casebench.__file__).parent
    for folder in ("judge", "metrics", "runs", "report", "cases", "extract"):
        for path in (root / folder).rglob("*.py"):
            code = "\n".join(
                line.split("#")[0] for line in path.read_text(encoding="utf-8").splitlines()
            )
            for name in providers:
                assert not re.search(rf"\b{name}\b", code), f"{path} names {name}"
    # A judge on any HTTP provider grades through the same calls, with only its own settings.
    reply = json.dumps([{"id": "c-f1", "met": True, "quote": "upheld"}])
    replies = {
        "openai": {"choices": [{"message": {"content": reply}}], "usage": {}},
        "anthropic": {"content": [{"type": "text", "text": reply}], "usage": {}},
    }
    case = evidenced_case()
    for name, body in replies.items():
        options = {"base_url": "http://127.0.0.1:1", "api_key_env": "ANY_KEY", "max_tokens": 64}

        def send(request: HttpRequest, body: dict[str, Any] = body) -> tuple[int, Any]:
            return 200, body

        judge = Judge(JudgeConfig(provider=name, model="m", options=options), send=send)
        grader = JudgeGrader(judge)
        assert "provider" not in inspect.signature(grader.grade).parameters
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("ANY_KEY", "a-key-of-the-users-own")
            [verdict] = grader.grade(case, "upheld", case.reference.criteria[:1])
        assert verdict == CriterionVerdict(criterion_id="c-f1", weight=1, met=True, quote="upheld")
        assert grader.kind is ScoreKind.LLM
