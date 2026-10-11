"""What a run would send, counted before anything is sent (decision 0028)."""

from dataclasses import dataclass

from casebench.config import CasebenchConfig
from casebench.core.case import Case
from casebench.corpus.cache import DEFAULT_CACHE, cached_documents
from casebench.judge import prompts

# OpenAI's published rule of thumb for English text; other languages differ (decision 0028).
CHARACTERS_PER_TOKEN = 4
CHECKED = "citation_integrity"


@dataclass(frozen=True)
class DryRun:
    target_calls: int
    target_input_tokens: int
    stored: int
    judge_calls_at_least: int
    judge_input_tokens_at_least: int
    candidates: int | None = None
    cached: int | None = None

    def lines(self) -> list[str]:
        out = [
            f"target: {self.target_calls} calls ({self.stored} cases already stored), about "
            f"{self.target_input_tokens} input tokens",
        ]
        if self.judge_calls_at_least:
            out.append(
                f"judge: at least {self.judge_calls_at_least} calls and "
                f"{self.judge_input_tokens_at_least} input tokens (one call per answer to list "
                "its citations, then two per citation, known only once the answers exist)"
            )
        if self.judge_calls_at_least and self.candidates is not None:
            out.append(
                f"corpus: one search per citation and up to {self.candidates} document fetches "
                f"each; {self.cached} documents already cached cost no call"
            )
        out += [
            f"tokens are rough: {CHARACTERS_PER_TOKEN} characters per token, and it varies "
            "by language",
            "nothing was sent",
        ]
        return out


def _tokens(characters: int) -> int:
    return characters // CHARACTERS_PER_TOKEN


def estimate(
    cases: list[Case], stored: set[str], config: CasebenchConfig, cache_root=DEFAULT_CACHE
) -> DryRun:
    pending = [case for case in cases if case.id not in stored]
    characters = sum(len(str(value)) for case in pending for value in case.task.inputs.values())
    checked = sum(1 for case in pending if CHECKED in case.metrics)
    corpus = config.corpus
    return DryRun(
        target_calls=len(pending),
        target_input_tokens=_tokens(characters),
        stored=len(cases) - len(pending),
        judge_calls_at_least=checked,
        judge_input_tokens_at_least=checked * _tokens(len(prompts.LIST_CITATIONS)),
        candidates=config.judge.candidates if config.judge and corpus else None,
        cached=cached_documents(corpus.connector, corpus.options, cache_root) if corpus else None,
    )
