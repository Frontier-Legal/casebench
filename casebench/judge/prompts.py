"""What the judge is asked while scoring: citations (decision 0026) and criteria (decision 0035)."""

import json
from typing import Any

LIST_CITATIONS = """You read an answer written by a legal AI system and list every authority it \
cites: court decisions, statutes, articles and regulations. Copy each citation exactly as the \
answer writes it, state the claim the answer makes with it in one sentence, say whether it \
is a statute (any legislation, article or regulation) or a court decision, and name the \
jurisdiction whose law or court it is as a code: one of the codes listed after the answer when \
there is such a list, otherwise an ISO 3166 code such as NO or US-CA, or EU for the European \
Union. Name a jurisdiction only where the citation itself shows it; otherwise give null. Do not \
judge whether the citations are right. Reply with JSON only: \
[{"citation": "...", "claim": "...", "kind": "statute" or "decision", \
"jurisdiction": "<code or null>"}]. Reply [] if the answer cites nothing."""

MATCH = """You decide which document a legal citation refers to. You get the citation and \
candidate documents from a search, each with its id, court, date, metadata and opening \
paragraph. Choose the candidate the citation refers to, or none if no candidate is that \
document; a document on the same topic is not the cited document. Reply with JSON only: \
{"document_id": "<id or null>", "reason": "..."}"""

WEIGH = """You decide whether a court decision or statute supports a claim an answer made \
when citing it. Read the whole document. Reply with JSON only: \
{"supports": true or false, "quote": "the passage that decides it, copied exactly", \
"reason": "..."}"""


GRADE = """You check an answer written by a legal AI system against criteria a lawyer wrote. \
You get the task, the reference facts with their evidence, the answer, and the criteria, each with \
an id and a weight. For each criterion decide whether the answer meets it; where a criterion says \
"Passes if ... Fails if ...", follow it. A criterion with a negative weight names something the \
answer must not do, and it is met when the answer does it. Judge only what the answer says. Quote \
the passage of the answer that decides each criterion, copied exactly, or give null when nothing \
in the answer bears on it. Reply with JSON only, one item per criterion in the order given: \
[{"id": "<criterion id>", "met": true or false, "quote": "<passage or null>"}]"""

# Every prompt the judge is asked while scoring; a score set records the hash of each.
ASKED = {"list_citations": LIST_CITATIONS, "match": MATCH, "weigh": WEIGH, "grade": GRADE}


def list_citations(answer: str, jurisdictions: list[str] | None = None) -> str:
    """`jurisdictions` are the codes the setup's corpora cover; None when any code may do."""
    listed = f"\n\nJurisdiction codes: {', '.join(jurisdictions)}" if jurisdictions else ""
    return f"Answer:\n{answer}{listed}"


def match(citation: str, candidates: list[dict[str, Any]]) -> str:
    listed = json.dumps(candidates, ensure_ascii=False, indent=2)
    return f"Citation: {citation}\n\nCandidates:\n{listed}"


def weigh(claim: str, document: dict[str, Any]) -> str:
    return (
        f"Claim: {claim}\n\nDocument {document['id']} ({document.get('court')}, "
        f"{document.get('date')}):\n{document.get('text', '')}"
    )


def grade(
    task: dict[str, Any], facts: list[dict[str, Any]], answer: str, criteria: list[dict[str, Any]]
) -> str:
    task_, facts_, criteria_ = (
        json.dumps(part, ensure_ascii=False, indent=2) for part in (task, facts, criteria)
    )
    return (
        f"Task:\n{task_}\n\nReference facts:\n{facts_}\n\nAnswer:\n{answer}\n\n"
        f"Criteria:\n{criteria_}"
    )
