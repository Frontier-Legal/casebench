"""What the judge is asked when it checks citations (decision 0026)."""

import json
from typing import Any

LIST_CITATIONS = """You read an answer written by a legal AI system and list every authority it \
cites: court decisions, statutes, articles and regulations. Copy each citation exactly as the \
answer writes it, and state the claim the answer makes with it in one sentence. Do not judge \
whether the citations are right. Reply with JSON only: \
[{"citation": "...", "claim": "..."}]. Reply [] if the answer cites nothing."""

MATCH = """You decide which document a legal citation refers to. You get the citation and \
candidate documents from a search, each with its id, court, date, metadata and opening \
paragraph. Choose the candidate the citation refers to, or none if no candidate is that \
document; a document on the same topic is not the cited document. Reply with JSON only: \
{"document_id": "<id or null>", "reason": "..."}"""

WEIGH = """You decide whether a court decision or statute supports a claim an answer made \
when citing it. Read the whole document. Reply with JSON only: \
{"supports": true or false, "quote": "the passage that decides it, copied exactly", \
"reason": "..."}"""


def list_citations(answer: str) -> str:
    return f"Answer:\n{answer}"


def match(citation: str, candidates: list[dict[str, Any]]) -> str:
    listed = json.dumps(candidates, ensure_ascii=False, indent=2)
    return f"Citation: {citation}\n\nCandidates:\n{listed}"


def weigh(claim: str, document: dict[str, Any]) -> str:
    return (
        f"Claim: {claim}\n\nDocument {document['id']} ({document.get('court')}, "
        f"{document.get('date')}):\n{document.get('text', '')}"
    )
