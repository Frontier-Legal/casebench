"""A second judge from another model family: an item passes only when both judges pass it."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import CasebenchConfig
from casebench.core.case import Case, Evidence, Fact, Reference, ReferenceSource, Task
from casebench.core.score import CitationLabel, Disagreement
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.metrics.base import score
from casebench.metrics.builtin.citation_integrity import CitationIntegrity
from casebench.metrics.builtin.criteria import Metric as Criteria
from casebench.metrics.builtin.precedent import Metric as Precedent
from casebench.report.render import lines
from casebench.runs.dry_run import estimate
from casebench.runs.log import Result
from tests.judge.fake_judge import DOUBTING, LOST, start_fake_judge
from tests.report.suites import criteria_case, frozen, outcome_case
from tests.test_citation_integrity import ANSWER, folder_corpus

FIRST = "Yargıtay 9. HD, E. 2023/1234 K. 2024/567"
SECOND = "Yargıtay 22. HD, E. 2022/77 K. 2023/90"
AGENTS = Path(__file__).parents[1] / "report" / "agents.py"


@pytest.fixture
def port(monkeypatch: pytest.MonkeyPatch) -> Iterator[int]:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_fake_judge()
    yield server.server_port
    server.shutdown()


def config(port: int, model: str, family: str) -> JudgeConfig:
    options = {"base_url": f"http://127.0.0.1:{port}", "max_tokens": 1024, "family": family}
    return JudgeConfig(provider="anthropic", model=model, options=options)


def judge(port: int, model: str, family: str) -> Judge:
    return Judge(config(port, model, family))


def case(metrics: list[str], facts: list[Fact] | None = None) -> Case:
    return Case(
        id="c1",
        task=Task.model_validate({"type": "qa", "question": "Is the dismissal valid?"}),
        reference=Reference(source=ReferenceSource.LAWYER, facts=facts or []),
        metrics=metrics,
    )


def test_a_citation_is_verified_only_when_both_judges_verify_it(tmp_path: Path, port: int):
    metric = CitationIntegrity(
        judge(port, "first-judge", "anthropic"),
        folder_corpus(tmp_path),
        candidates=5,
        second_judge=judge(port, DOUBTING, "other"),
    )
    asked = case(["citation_integrity"])

    scored = score(metric, asked, Result(case_id="c1", output=ANSWER))

    labels = {c.citation: c.label for c in scored.citations}
    assert labels[FIRST] is CitationLabel.MISGROUNDED  # the first judge alone verified it
    assert scored.value == 0.0
    assert scored.judged_twice == 3
    assert scored.disagreements == [
        Disagreement(item=FIRST, first="verified", second="misgrounded")
    ]
    printed = lines([], [scored])
    assert "  citation_integrity: agreed on 2 of 3 items (67%)" in printed
    assert f"    c1 · citation_integrity · {FIRST}: first verified, second misgrounded" in printed


def test_an_authority_counts_only_when_both_judges_name_its_document(tmp_path: Path, port: int):
    court = Fact(
        id="p1", kind="precedent", value=FIRST, evidence=Evidence(doc="d"), document_id="corpus:101"
    )
    corpus = folder_corpus(tmp_path)
    asked = case(["precedent"], [court])
    answer = Result(case_id="c1", output=ANSWER)
    alone = Precedent(judge(port, "first-judge", "anthropic"), corpus, candidates=5)
    both = Precedent(
        judge(port, "first-judge", "anthropic"),
        corpus,
        candidates=5,
        second_judge=judge(port, LOST, "other"),
    )

    one, two = score(alone, asked, answer), score(both, asked, answer)

    assert one.value > 0.0
    assert two.value == 0.0
    assert [d.item for d in two.disagreements] == [FIRST, SECOND]
    assert two.disagreements[0] == Disagreement(
        item=FIRST, first="corpus:101", second="no document"
    )


def test_two_judges_of_one_family_are_refused(tmp_path: Path, port: int):
    suite = frozen(
        [outcome_case(1, "reversed", "The appeal court found an error.")], tmp_path / "s"
    )
    options = f"{{base_url: 'http://127.0.0.1:{port}', max_tokens: 1024}}"
    path = tmp_path / "casebench.yaml"
    path.write_text(
        "judges:\n"
        f"  - {{provider: anthropic, model: first-judge, options: {options}}}\n"
        f"  - {{provider: anthropic, model: second-judge, options: {options}}}\n",
        encoding="utf-8",
    )

    ran = CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(suite),
            "--config",
            str(path),
            "--python",
            f"{AGENTS}:upheld",
            "--runs-dir",
            str(tmp_path / "runs"),
        ],
    )

    assert ran.exit_code == 1
    assert "both judges are of the anthropic family" in ran.output
    assert not (tmp_path / "runs").exists()


def test_the_dry_run_counts_the_second_judges_calls(port: int):
    two = CasebenchConfig(
        judges=[config(port, "first-judge", "anthropic"), config(port, DOUBTING, "other")]
    )

    printed = "\n".join(estimate([case(["citation_integrity"])], set(), two).lines())

    assert "one per citation to weigh it for each of the 2 judges" in printed


def test_a_criterion_passes_only_when_both_judges_pass_it(port: int):
    metric = Criteria(
        judge(port, "first-judge", "anthropic"), second_judge=judge(port, DOUBTING, "other")
    )
    asked = criteria_case(1, {"Mentions upheld": 2, "Mentions reversed": -1})

    scored = score(metric, asked, Result(case_id=asked.id, output="The decision is upheld."))

    assert scored.label == "failed: c1"
    assert scored.value == 0.0
    assert scored.judged_twice == 2
    assert scored.disagreements == [
        Disagreement(item="criterion c1", first="passed", second="failed")
    ]
