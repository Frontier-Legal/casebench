"""One case from the corpus's own search, drafted, asked and graded: how setup ends (0045)."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

from casebench.cases.build import Written, lawyer_case
from casebench.cases.draft import Draft, draft
from casebench.config import CasebenchConfig
from casebench.core.case import Approval, Case, Criterion, Evidence, Fact
from casebench.corpus.corpora import Corpora
from casebench.corpus.results import SearchResult
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.metrics.base import Verdict
from casebench.metrics.loading import build
from casebench.runs.log import Result
from casebench.runs.scoring import context_for
from casebench.targets.sample import send_case

CASE_ID = "demo-1"
AUTHOR = "casebench demo"
CITES = "c-cites-decision"
DECISION_FACT = "decision-1"


class DemoNeeds(ValueError):
    """The config lacks what the demo needs, said with what to add."""


@dataclass(frozen=True)
class Plan:
    """What the demo will spend, said before anything is sent."""

    corpus: str
    probe: str
    drafter: JudgeConfig
    graders: list[JudgeConfig]

    def lines(self) -> list[str]:
        graders = " and ".join(f"{g.provider}/{g.model}" for g in self.graders)
        return [
            f"1 search of {self.corpus} for {self.probe!r}, for 1 result",
            "1 document fetched",
            f"1 call to {self.drafter.provider}/{self.drafter.model} to draft the case",
            "1 turn of your agent",
            f"{len(self.graders)} call{'s' if len(self.graders) > 1 else ''} to {graders} "
            "to grade the answer",
        ]


@dataclass(frozen=True)
class Demo:
    """The case, the agent's answer, and the grade, with what the decision's citation is."""

    case: Case
    drafted: Draft
    citation: str
    result: Result
    verdict: Verdict | None


def plan(config: CasebenchConfig) -> Plan:
    """Which corpus is searched with which search, and which models draft and grade."""
    probed = [(name, c.probe) for name, c in config.corpora.items() if c.probe]
    if not probed:
        raise DemoNeeds("the demo searches the corpus with its probe: add it with --probe TEXT")
    if not config.judges:
        raise DemoNeeds("the demo grades the answer with the judge: add `judge:` to the config")
    if config.target is None:
        raise DemoNeeds("the demo asks the agent: add `target:` to the config")
    drafter = config.extract.models[0] if config.extract else config.judges[0]
    name, probe = probed[0]
    return Plan(corpus=name, probe=str(probe), drafter=drafter, graders=list(config.judges))


def _citation(found: SearchResult, drafted: Draft) -> str:
    """How the corpus cites the decision, or else its court and date."""
    decision = drafted.decision
    return found.citation or f"{decision.court}, {decision.date}"


def _case(drafted: Draft, citation: str) -> Case:
    """The drafted case as a draft, with one more criterion that Casebench writes: the answer
    cites the decision the question came from."""
    reading = drafted.reading
    written = Written(
        question=drafted.question,
        facts=reading.facts,
        outcome=reading.outcome.value if reading.outcome else None,
        statutes=[item.value for item in reading.statutes],
        precedents=[item.value for item in reading.precedents],
    )
    made = lawyer_case(CASE_ID, written, AUTHOR, drafted)
    decision = drafted.decision.id
    itself = Fact(
        id=DECISION_FACT,
        kind="decision",
        value=citation,
        evidence=Evidence(doc=decision, note="the decision this case was drafted from"),
        document_id=decision,
    )
    cites = Criterion(
        id=CITES,
        text=f"Passes if the answer cites the decision {citation}, in any form that "
        "identifies it. Fails if it does not.",
        weight=1,
        derived_from=[DECISION_FACT],
    )
    reference = made.reference.model_copy(
        update={
            "facts": [*made.reference.facts, itself],
            "criteria": [*made.reference.criteria, cites],
        }
    )
    return made.model_copy(update={"reference": reference, "approval": Approval.DRAFT})


def run_demo(config: CasebenchConfig, chosen: Plan) -> Demo:
    """Exactly what the plan says: one search, one fetch, one drafting call, one agent turn,
    and one grading call for each judge."""
    corpora = Corpora(config.corpora)
    found = corpora.search_results(chosen.probe, 1, names=[chosen.corpus])
    if not found:
        raise DemoNeeds(f"{chosen.corpus} found nothing for {chosen.probe!r}; add it again with "
                        "a probe that finds a decision")  # fmt: skip
    drafted = draft(Judge(chosen.drafter), corpora.decision(found[0].id))
    if not drafted.question:
        raise DemoNeeds("the drafting model wrote no question for this decision; run it again")
    citation = _citation(found[0], drafted)
    case = _case(drafted, citation)
    result = asyncio.run(send_case(config, case))
    verdict = None
    if result.output is not None:
        verdict = build("criteria", context_for(config)).judge(case, result)
    return Demo(case, drafted, citation, result, verdict)


def keep(demo: Demo, folder: Path) -> Path:
    """The case and the agent's answer, kept as a draft a lawyer may approve into a suite."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "case.json").write_text(demo.case.model_dump_json(indent=2), encoding="utf-8")
    (folder / "answer.json").write_text(demo.result.model_dump_json(indent=2), encoding="utf-8")
    return folder
