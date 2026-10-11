"""Parse citations out of a plain-text answer with the configured jurisdiction's adapter."""

from casebench.adapters.interface import JurisdictionAdapter
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.targets.answer import CitationParser


def citation_parser(jurisdiction: str, source: str | None = None) -> CitationParser:
    """The adapter's normalised keys, in the order the answer cites them."""
    adapter: JurisdictionAdapter = registry.load(kind_named("adapter"), jurisdiction, source)()

    def parse(text: str) -> list[str]:
        return [citation.key for citation in adapter.citations(text)]

    return parse
