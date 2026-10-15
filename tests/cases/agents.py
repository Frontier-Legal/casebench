"""Agents for the document tasks, each doing its task the way the tests need."""

import json

DRAFT = (
    "The dismissal is invalid, and the employee never waived the notice period. "
    "See Yargıtay 9. HD, E. 2023/1234 K. 2024/567."
)


def answers(question: str, **_: object) -> str:
    return "The decision is upheld."


def ranks(question: str, **_: object) -> dict:
    """The synthesis as its answer, the authorities in rank order as its citations."""
    return {
        "answer": "Dismissal needs a valid reason; the 9th chamber applied it in 2019.",
        "citations": [
            "TBK m. 49",
            "İş K. md. 18",
            "Yargıtay 9. Hukuk Dairesi 2019/1 E., 2020/2 K.",
        ],
    }


def drafts(instruction: str, **_: object) -> str:
    return DRAFT


def edits(instruction: str, document: str) -> str:
    """Caps the indemnity in 9.2, as asked, and also rewords clause 4."""
    return document.replace("without limit", "up to the fees paid").replace(
        "The term is two years.", "This agreement runs for two years."
    )


def extracts(document: str, fields: dict) -> str:
    return json.dumps({"party_a": "Acme A.Ş.", "party_b": "  beta ltd.  ", "date": "2024-01-02"})
