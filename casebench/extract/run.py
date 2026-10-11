"""Read decisions with two models and keep the answer keys they agree on."""

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casebench.corpus.binding import Corpus
from casebench.extract.agreement import FIELDS, agreed_fields, key_facts
from casebench.extract.prompt import EXTRACT, decision_prompt
from casebench.extract.reading import Reading, read_reply
from casebench.judge.client import Judge
from casebench.references.court import AnswerKey

KEYS_FILE = "keys.jsonl"
REPORT_FILE = "extraction.json"


@dataclass
class Extraction:
    decisions: int = 0
    keys: list[AnswerKey] = field(default_factory=list)
    agreed: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    failures: list[str] = field(default_factory=list)

    def rate(self, name: str) -> float:
        read = self.decisions - len(self.failures)
        return self.agreed[name] / read if read else 0.0


def _read(model: Judge, text: str) -> Reading:
    return read_reply(text, model.ask(EXTRACT, decision_prompt(text)))


def _one(corpus: Corpus, models: list[Judge], decision_id: str) -> tuple[AnswerKey | None, dict]:
    record = corpus.decision(decision_id)
    first, second = (_read(model, record.text) for model in models)
    agreed = agreed_fields(first, second)
    facts = key_facts(decision_id, first, agreed)
    if not facts or not agreed["facts"]:
        return None, agreed
    key = AnswerKey(
        decision_id=decision_id,
        jurisdiction=record.jurisdiction,
        inputs={"facts": first.facts},
        facts=facts,
        date=record.date,
        court=record.court,
        level=record.level,
    )
    return key, agreed


def extract(
    corpus: Corpus,
    models: list[Judge],
    ids: list[str],
    *,
    workers: int = 1,
    progress: Callable[[int], None] | None = None,
) -> Extraction:
    """Each decision read by both models; a failure is that decision's, not the run's."""
    result = Extraction(decisions=len(ids))

    def attempt(decision_id: str) -> tuple[str, Any]:
        try:
            return decision_id, _one(corpus, models, decision_id)
        except Exception as error:
            return decision_id, error

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for done, (decision_id, outcome) in enumerate(pool.map(attempt, ids), start=1):
            if isinstance(outcome, Exception):
                result.failures.append(f"{decision_id}: {type(outcome).__name__}: {outcome}")
            else:
                key, agreed = outcome
                for name, ok in agreed.items():
                    result.agreed[name] += ok
                if key is not None:
                    result.keys.append(key)
            if progress:
                progress(done)
    return result


def write(result: Extraction, models: list[Judge], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / KEYS_FILE).open("w", encoding="utf-8") as stream:
        for key in result.keys:
            stream.write(key.model_dump_json() + "\n")
    report = {
        "decisions": result.decisions,
        "keys": len(result.keys),
        "fields": {
            name: {"agreed": result.agreed[name], "rate": result.rate(name)} for name in FIELDS
        },
        "models": [
            {
                "provider": m.config.provider,
                "model": m.config.model,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
            }
            for m in models
        ],
        "failures": result.failures,
    }
    (folder / REPORT_FILE).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def read_keys(folder: Path) -> list[AnswerKey]:
    lines = (folder / KEYS_FILE).read_text(encoding="utf-8").splitlines()
    return [AnswerKey.model_validate_json(line) for line in lines if line]
