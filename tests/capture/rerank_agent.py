"""An agent whose search and rerank are plain Python functions in its own process."""

from dataclasses import dataclass


@dataclass
class Hit:
    id: str
    score: float


def search(query: str) -> list[Hit]:
    return [Hit("tr-1", 0.9), Hit("tr-2", 0.8), Hit("tr-3", 0.7)]


def rerank(query: str, candidates: list[Hit]) -> list[Hit]:
    return [hit for hit in candidates if hit.id != "tr-2"]


def answer(question: str) -> dict:
    kept = rerank(question, search(question))
    return {"answer": "Invalid.", "documents": [hit.id for hit in kept]}
