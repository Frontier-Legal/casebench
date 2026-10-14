"""Read decisions with two models and keep the answer keys they agree on."""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casebench.corpus.binding import Corpus
from casebench.corpus.ids import SEPARATOR
from casebench.extract.agreement import FIELDS, agreed_fields, key_facts
from casebench.extract.prompt import EXTRACT, decision_prompt
from casebench.extract.reading import Reading, read_reply
from casebench.judge.client import Judge
from casebench.references.court import AnswerKey

KEYS_FILE = "keys.jsonl"
REPORT_FILE = "extraction.json"


@dataclass
class Extraction:
    """`seconds` is the whole run's wall time and `per_decision` each decision's (0038)."""

    decisions: int = 0
    keys: list[AnswerKey] = field(default_factory=list)
    agreed: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FIELDS, 0))
    failures: list[str] = field(default_factory=list)
    seconds: float = 0.0
    per_decision: list[float] = field(default_factory=list)

    @property
    def read(self) -> int:
        return self.decisions - len(self.failures)

    def rate(self, name: str) -> float:
        return self.agreed[name] / self.read if self.read else 0.0


@dataclass(frozen=True)
class Progress:
    """One decision finished: which, how long it took, and how many are done of how many."""

    done: int
    total: int
    decision_id: str
    seconds: float
    failed: bool


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
        extracted_by=[f"{m.config.provider}/{m.config.model}" for m in models],
    )
    return key, agreed


def extract(
    corpus: Corpus,
    models: list[Judge],
    ids: list[str],
    *,
    workers: int = 1,
    progress: Callable[[Progress], None] | None = None,
) -> Extraction:
    """Each decision read by both models; a failure is that decision's, not the run's. The
    time of each decision and of the whole run is kept, so settings can be compared (0038)."""
    result = Extraction(decisions=len(ids))
    started = time.perf_counter()

    def attempt(decision_id: str) -> tuple[str, Any, float]:
        begun = time.perf_counter()
        try:
            outcome: Any = _one(corpus, models, decision_id)
        except Exception as error:
            outcome = error
        return decision_id, outcome, time.perf_counter() - begun

    with ThreadPoolExecutor(max_workers=workers) as pool:
        finished = enumerate(pool.map(attempt, ids), start=1)
        for done, (decision_id, outcome, seconds) in finished:
            failed = isinstance(outcome, Exception)
            if failed:
                result.failures.append(f"{decision_id}: {type(outcome).__name__}: {outcome}")
            else:
                key, agreed = outcome
                for name, ok in agreed.items():
                    result.agreed[name] += ok
                if key is not None:
                    result.keys.append(key)
                result.per_decision.append(seconds)
            if progress:
                progress(Progress(done, len(ids), decision_id, seconds, failed))
    result.seconds = time.perf_counter() - started
    return result


def write(result: Extraction, models: list[Judge], folder: Path, corpus: str) -> None:
    """The keys this run made replace the ones earlier runs made from the same corpus; keys
    from other corpora stay, so one folder can hold keys from several (decision 0036)."""
    folder.mkdir(parents=True, exist_ok=True)
    others = [
        key
        for key in (read_keys(folder) if (folder / KEYS_FILE).is_file() else [])
        if key.decision_id.partition(SEPARATOR)[0] != corpus
    ]
    with (folder / KEYS_FILE).open("w", encoding="utf-8") as stream:
        for key in [*others, *result.keys]:
            stream.write(key.model_dump_json() + "\n")
    costs = [m.cost for m in models]
    report = {
        "decisions": result.decisions,
        "read": result.read,
        "keys": len(result.keys),
        "fields": {
            name: {"agreed": result.agreed[name], "rate": result.rate(name)} for name in FIELDS
        },
        "models": [
            {
                "provider": m.config.provider,
                "model": m.config.model,
                "settings": m.settings,
                "calls": m.calls,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "cost": m.cost,
            }
            for m in models
        ],
        "seconds": {
            "total": result.seconds,
            "per_decision": result.per_decision,
        },
        # Unknown when any model has no price in casebench.yaml (decision 0038).
        "cost": None if None in costs else sum(c for c in costs if c is not None),
        "failures": result.failures,
    }
    (folder / REPORT_FILE).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def read_keys(folder: Path) -> list[AnswerKey]:
    lines = (folder / KEYS_FILE).read_text(encoding="utf-8").splitlines()
    return [AnswerKey.model_validate_json(line) for line in lines if line]
