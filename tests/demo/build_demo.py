"""Write the project `casebench demo` copies: its suite, corpus, agent answers and judge memo.

Run `uv run python -m tests.demo.build_demo` after a judge prompt changes. The cases, the
documents and the answers are written for the demo; none is a real decision or real advice. The
judge's replies come from the scripted judge below, which reads each prompt as a careful model
would for these few cases, and are kept as the run's memo keeps a model's (decision 0061).
"""

import contextlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

from casebench.config import load_config
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
from casebench.demo import PROJECT, write_config
from casebench.judge import client, prompts
from casebench.judge.memo import MEMO_FILE
from casebench.providers.interface import Completion
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.scoring import score
from casebench.suites.freeze import freeze, load

COURT = "Court of Appeal of Examplia"
DOCUMENTS = [
    {
        "id": "CA-2024-11",
        "date": "2024-03-12",
        "text": (
            "CA 2024/11. Examplia Court of Appeal, Labour Chamber. The employer dismissed the "
            "claimant by telephone. Held: a dismissal that is not given in writing is void. The "
            "employer must reinstate the employee or pay compensation of at least four months' "
            "wages, at the employee's choice."
        ),
    },
    {
        "id": "CA-2023-07",
        "date": "2023-06-02",
        "text": (
            "CA 2023/07. Examplia Court of Appeal, Labour Chamber. The claimant was dismissed in "
            "the second month of a three-month probation period. Held: during an agreed "
            "probation period of at most three months either party may end the contract without "
            "giving a reason. Notice of one week is still owed."
        ),
    },
    {
        "id": "CA-2022-31",
        "date": "2022-11-21",
        "text": (
            "CA 2022/31. Examplia Court of Appeal, Labour Chamber. The claimant sought pay for "
            "overtime worked over six years. Held: a claim for overtime pay is barred five years "
            "after the pay day on which it fell due. Only the last five years may be recovered."
        ),
    },
    {
        "id": "CA-2024-02",
        "date": "2024-01-30",
        "text": (
            "CA 2024/02. Examplia Court of Appeal, Labour Chamber. The claimant resigned after "
            "their pay was withheld for three months. Held: a resignation the employer forced by "
            "a serious breach is treated as a dismissal by the employer, and the employee keeps "
            "every claim a dismissed employee has."
        ),
    },
    {
        "id": "CA-2021-19",
        "date": "2021-09-14",
        "text": (
            "CA 2021/19. Examplia Court of Appeal, Labour Chamber. Held: a clause forbidding an "
            "employee to work for a competitor after leaving binds the employee only when the "
            "employer pays compensation for the restricted period. Without compensation the "
            "clause is unenforceable."
        ),
    },
]

QUESTIONS = {
    "written-notice": (
        "My employer fired me over the phone yesterday. Is that a valid dismissal under "
        "Examplia law, and what can I claim?"
    ),
    "probation": (
        "We want to let a new hire go in month two of a three-month probation period. Do we "
        "need a reason, and do we owe notice?"
    ),
    "overtime": "How far back can an employee in Examplia claim unpaid overtime?",
    "forced-resignation": (
        "I resigned because my employer stopped paying me for three months. Have I lost my "
        "claims because I resigned?"
    ),
    "non-compete": (
        "My contract says I cannot work for a competitor for a year after leaving, and pays "
        "nothing for it. Is that binding?"
    ),
    "compensation": (
        "If a dismissal is void in Examplia, how much compensation can the employee ask for "
        "instead of going back to work?"
    ),
}

# The demo agent's answer to each case: some right, some citing a decision that says something
# else, one citing a decision that is not in the corpus.
ANSWERS = {
    "written-notice": (
        "A dismissal given only by telephone is void: Examplia requires a dismissal in writing "
        "(CA 2024/11). You may ask to be reinstated, or take compensation of at least four "
        "months' wages instead."
    ),
    "probation": (
        "No reason is needed while the probation period lasts (CA 2023/07), so you may end the "
        "contract now."
    ),
    "overtime": (
        "Overtime pay is barred two years after it fell due (CA 2022/31), so only the last two "
        "years can be claimed."
    ),
    "forced-resignation": (
        "No. A resignation forced by the employer's serious breach counts as a dismissal "
        "(CA 2019/88), so you keep your claims."
    ),
    "non-compete": (
        "It is not binding: a non-compete clause without compensation is unenforceable "
        "(CA 2021/19)."
    ),
    "compensation": (
        "The employee may claim compensation of at least four months' wages (CA 2024/02)."
    ),
}

# Each case's criteria, as a lawyer would write them, with the words a met criterion's answer
# says: the scripted judge finds a criterion met when the answer says them all.
CRITERIA: dict[str, list[tuple[str, int, list[str]]]] = {
    "written-notice": [
        ("States that a dismissal not given in writing is void.", 3, ["void", "writing"]),
        ("Names reinstatement or four months' wages as the remedy.", 2, ["four months"]),
    ],
    "probation": [
        ("States that no reason is needed during probation.", 2, ["no reason"]),
        ("Says that one week's notice is still owed.", 2, ["week"]),
    ],
    "overtime": [
        ("States the five-year limit for overtime claims.", 3, ["five years"]),
    ],
    "forced-resignation": [
        ("Says the resignation is treated as a dismissal.", 3, ["counts as a dismissal"]),
        ("Says the employee keeps the claims of a dismissed employee.", 1, ["keep"]),
    ],
    "non-compete": [
        ("States that the clause is unenforceable without compensation.", 3, ["unenforceable"]),
    ],
    "compensation": [
        ("States at least four months' wages.", 3, ["four months"]),
        ("Mentions that the employee chooses between reinstatement and compensation.", 1,
         ["reinstate"]),
    ],
}  # fmt: skip

# What each decision decides, for the scripted judge's weighing: a claim is supported when it
# says each of the words listed for the decision it cites.
HOLDS = {
    "CA-2024-11": ["writing"],
    "CA-2023-07": ["no reason"],
    "CA-2022-31": ["five years"],
    "CA-2024-02": ["dismissal"],
    "CA-2021-19": ["compensation"],
}
CITATION = re.compile(r"CA (\d{4})/(\d+)")
# The decision each case's reference rests on.
GROUNDS = {
    "written-notice": "CA-2024-11",
    "probation": "CA-2023-07",
    "overtime": "CA-2022-31",
    "forced-resignation": "CA-2024-02",
    "non-compete": "CA-2021-19",
    "compensation": "CA-2024-11",
}


def held(document_id: str) -> str:
    """What a decision holds, as its text says after "Held: "."""
    text = next(d["text"] for d in DOCUMENTS if d["id"] == document_id)
    return text.split("Held: ", 1)[1]


def fact(case_id: str) -> Fact:
    document_id = GROUNDS[case_id]
    rule = held(document_id)
    return Fact(
        id="f1",
        kind="rule",
        value=rule,
        evidence=Evidence(doc=document_id, quote=rule),
        document_id=document_id,
    )


def cases() -> list[Case]:
    return [
        Case(
            id=case_id,
            task=Task.model_validate({"type": "qa", "question": question}),
            reference=Reference(
                source=ReferenceSource.LAWYER,
                author="demo",
                facts=[fact(case_id)],
                criteria=[
                    Criterion(id=f"c{number}", text=text, weight=weight, derived_from=["f1"])
                    for number, (text, weight, _) in enumerate(CRITERIA[case_id], start=1)
                ],
            ),
            metrics=["citation_integrity", "criteria"],
            approval=Approval.APPROVED,
            practice_area="employment",
        )
        for case_id, question in QUESTIONS.items()
    ]


def _listed(user: str) -> list[dict[str, Any]]:
    answer = user.removeprefix("Answer:\n").split("\n\nJurisdiction codes:")[0]
    listed = []
    for sentence in re.split(r"(?<=\.)\s+", answer):
        for found in CITATION.finditer(sentence):
            listed.append(
                {"citation": found.group(0), "claim": sentence, "kind": "decision",
                 "jurisdiction": None}
            )  # fmt: skip
    return listed


def _matched(user: str) -> list[dict[str, Any]]:
    picked = []
    for item in json.loads(user.split("Citations:\n", 1)[1]):
        # The candidate the corpus cites by the docket the citation names.
        found = CITATION.search(item["as_written"])
        cited = f"CA-{found.group(1)}-{found.group(2)}.json" if found else None
        chosen = next((c["id"] for c in item["candidates"] if c.get("citation") == cited), None)
        picked.append({"citation": item["citation"], "document_id": chosen, "reason": "docket"})
    return picked


def _weighed(user: str) -> dict[str, Any]:
    claim = user.removeprefix("Claim: ").split("\n\nDocument ", 1)[0].casefold()
    document_id = user.split("\n\nDocument ", 1)[1].split(" ", 1)[0]
    supports = all(word in claim for word in HOLDS[document_id])
    quote = held(document_id).split(". ", 1)[0].removesuffix(".") + "."
    reason = "the decision holds this" if supports else "the decision holds something else"
    return {"supports": supports, "quote": quote, "reason": reason}


def _graded(user: str) -> list[dict[str, Any]]:
    answer, criteria = user.split("\n\nAnswer:\n", 1)[1].split("\n\nCriteria:\n", 1)
    question = json.loads(user.split("Task:\n", 1)[1].split("\n\nReference facts:", 1)[0])
    case_id = next(c for c, q in QUESTIONS.items() if q == question["question"])
    words = {f"c{n}": said for n, (_, _, said) in enumerate(CRITERIA[case_id], start=1)}
    graded = []
    for criterion in json.loads(criteria):
        met = all(word in answer.casefold() for word in words[criterion["id"]])
        graded.append({"id": criterion["id"], "met": met, "quote": answer if met else None})
    return graded


def reply(system: str, user: str) -> Any:
    if system == prompts.LIST_CITATIONS:
        return _listed(user)
    if system == prompts.MATCH:
        return _matched(user)
    if system == prompts.WEIGH:
        return _weighed(user)
    if system == prompts.GRADE:
        return _graded(user)
    raise AssertionError(f"the demo's judge was asked something new: {system[:60]}")


def scripted(provider: Any, messages: list[Any], model: str, send: Any) -> Completion:
    system, user = messages[0].content, messages[1].content
    text = json.dumps(reply(system, user), ensure_ascii=False)
    return Completion(text=text, input_tokens=0, output_tokens=0)


def build(project: Path = PROJECT) -> None:
    if project.exists():
        shutil.rmtree(project)
    corpus = project / "corpus"
    corpus.mkdir(parents=True)
    for document in DOCUMENTS:
        record = {**document, "jurisdiction": "xx", "court": COURT}
        (corpus / f"{document['id']}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    by_question = {QUESTIONS[case_id]: answer for case_id, answer in ANSWERS.items()}
    (project / "answers.json").write_text(
        json.dumps(by_question, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    freeze("demo", cases(), project / "suite", {"written_for": "the casebench demo"})
    # In a new folder, so the corpus is read from the files just written and not from a cache
    # an earlier build left in this one.
    with tempfile.TemporaryDirectory() as scratch, contextlib.chdir(scratch):
        folder = Path(scratch)
        config_path = write_config(project.resolve(), folder)
        config = load_config(config_path)
        manifest, suite = load(project / "suite")
        log = RunLog.create(
            folder / "run",
            RunInfo(
                run_id="demo",
                suite_id=manifest.suite_id,
                suite_hash=manifest.content_hash,
                target="python",
            ),
        )
        for case_id, answer in ANSWERS.items():
            log.append(Result(case_id=case_id, repeat=0, output=answer))
        with mock.patch.object(client, "complete", scripted):
            score(log, suite, config, manifest.suite_id)
        shutil.copyfile(log.folder / MEMO_FILE, project / MEMO_FILE)


if __name__ == "__main__":
    build()
    print(f"wrote {PROJECT}")
