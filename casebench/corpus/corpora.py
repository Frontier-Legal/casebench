"""Every corpus a setup names, read as one: searched together, each id fetched from its own."""

import threading
from pathlib import Path
from typing import Any

from casebench.corpus.binding import Corpus, CorpusConfig
from casebench.corpus.cache import DEFAULT_CACHE
from casebench.corpus.ids import UnqualifiedId, split
from casebench.corpus.record import DecisionRecord
from casebench.corpus.results import SearchResult


class NoSuchCorpus(ValueError):
    """A command named a corpus the setup does not have, or needs a name to choose one."""


class Corpora:
    """Each corpus is opened when it is first used, so a store a command never reads is never
    started or called."""

    def __init__(self, configs: dict[str, CorpusConfig], cache_root: Path = DEFAULT_CACHE) -> None:
        self.configs = configs
        self.cache_root = cache_root
        self.opened: dict[str, Corpus] = {}
        # Cases are scored in parallel (decision 0037); each store is still opened once.
        self.opening = threading.Lock()

    @property
    def names(self) -> list[str]:
        return list(self.configs)

    def named(self, name: str) -> Corpus:
        if name not in self.configs:
            known = ", ".join(self.names) or "none"
            raise NoSuchCorpus(f"the config has no corpus named {name} (it has: {known})")
        with self.opening:
            if name not in self.opened:
                self.opened[name] = Corpus(self.configs[name], name, self.cache_root)
            return self.opened[name]

    def only(self, name: str | None) -> Corpus:
        """The corpus a command reads: the one named, or the setup's only one."""
        if name is not None:
            return self.named(name)
        if len(self.configs) != 1:
            known = ", ".join(self.names) or "none"
            raise NoSuchCorpus(f"name the corpus with --corpus; the config has: {known}")
        return self.named(self.names[0])

    def raw(self, qualified: str) -> dict[str, Any]:
        corpus, _ = split(qualified)
        try:
            return self.named(corpus).raw(qualified)
        except NoSuchCorpus as error:
            raise UnqualifiedId(str(error)) from error

    def decision(self, qualified: str) -> DecisionRecord:
        return self.named(split(qualified)[0]).decision(qualified)

    def search(self, text: str, limit: int, names: list[str] | None = None) -> list[str]:
        """Up to `limit` ids from each corpus named (every one when none are), taken in turn:
        every corpus's best first. A corpus not named is never searched."""
        return [result.id for result in self.search_results(text, limit, names)]

    def search_results(
        self, text: str, limit: int, names: list[str] | None = None, kind: str | None = None
    ) -> list[SearchResult]:
        """As `search`, with what each corpus says about its results, each searched with its
        filters for `kind`."""
        searched = self.names if names is None else names
        found = [self.named(name).search_results(text, limit, kind) for name in searched]
        merged = []
        for rank in range(limit):
            merged += [results[rank] for results in found if rank < len(results)]
        return merged
