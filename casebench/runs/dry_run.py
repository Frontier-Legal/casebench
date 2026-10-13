"""What a run would send, counted before anything is sent (decision 0028)."""

from dataclasses import dataclass, field
from pathlib import Path

from casebench.config import CasebenchConfig
from casebench.core.case import Case
from casebench.corpus.cache import DEFAULT_CACHE, cached_documents, cached_searches
from casebench.corpus.routing import route
from casebench.judge import prompts

# OpenAI's published rule of thumb for English text; other languages differ (decision 0028).
CHARACTERS_PER_TOKEN = 4
JUDGED = ("citation_integrity", "statute", "precedent")


@dataclass(frozen=True)
class DryRun:
    target_calls: int
    target_input_tokens: int
    stored: int
    judge_calls_at_least: int
    judge_input_tokens_at_least: int
    candidates: int | None = None
    cached: int | None = None
    searches_cached: int = 0
    corpora: dict[str, tuple[int, int, int]] = field(default_factory=dict)

    def lines(self) -> list[str]:
        out = [
            f"target: {self.target_calls} calls ({self.stored} cases already stored), about "
            f"{self.target_input_tokens} input tokens",
        ]
        if self.judge_calls_at_least:
            out.append(
                f"judge: at least {self.judge_calls_at_least} calls and "
                f"{self.judge_input_tokens_at_least} input tokens (one call per answer to list "
                "its citations, then up to two per citation, known only once the answers exist)"
            )
        if self.judge_calls_at_least and self.candidates is not None:
            out.append(
                f"corpus: one search per citation and up to {self.candidates} document fetches "
                f"each; {self.cached} documents and {self.searches_cached} searches already "
                "cached cost no call"
            )
            for name, (answers, cached, searches) in self.corpora.items():
                out.append(
                    f"  {name}: searched for the citations in up to {answers} answers, by the "
                    f"case's jurisdiction; {cached} documents and {searches} searches cached"
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
    checked = sum(1 for case in pending if set(JUDGED) & set(case.metrics))
    corpora = config.corpora.values()
    return DryRun(
        target_calls=len(pending),
        target_input_tokens=_tokens(characters),
        stored=len(cases) - len(pending),
        judge_calls_at_least=checked,
        judge_input_tokens_at_least=checked * _tokens(len(prompts.LIST_CITATIONS)),
        candidates=config.judge.candidates if config.judge and corpora else None,
        cached=(
            sum(cached_documents(c.connector, c.options, cache_root) for c in corpora)
            if corpora
            else None
        ),
        searches_cached=sum(cached_searches(c.connector, c.options, cache_root) for c in corpora),
        corpora=_per_corpus(pending, config, cache_root) if len(config.corpora) > 1 else {},
    )


def _per_corpus(
    pending: list[Case], config: CasebenchConfig, cache_root: Path
) -> dict[str, tuple[int, int, int]]:
    """For each corpus, how many judged answers its jurisdiction routing can send to it, so a
    metered provider's share shows before a run (decision 0036); a case with no jurisdiction
    may send to every corpus."""
    reach = {name: 0 for name in config.corpora}
    for case in pending:
        if not set(JUDGED) & set(case.metrics):
            continue
        place = case.provenance.jurisdiction if case.provenance else None
        for name in route(config.corpora, None, None, place).names:
            reach[name] += 1
    return {
        name: (
            reach[name],
            cached_documents(c.connector, c.options, cache_root),
            cached_searches(c.connector, c.options, cache_root),
        )
        for name, c in config.corpora.items()
    }
