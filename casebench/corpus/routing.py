"""Which corpora a citation is searched in: by its jurisdiction and kind, else the case's (0036)."""

from dataclasses import dataclass
from enum import StrEnum

from casebench.core.jurisdiction import UnknownJurisdiction, code
from casebench.corpus.binding import CorpusConfig

# What a corpus `holds` for each kind of citation the judge names.
HOLDING = {"decision": "decisions", "statute": "statutes"}


class Route(StrEnum):
    """What chose the corpora: the citation's own jurisdiction, the case's, or neither."""

    CITATION = "citation"
    CASE = "case"
    ALL = "all"


@dataclass(frozen=True)
class Routing:
    """The corpora to search, in the config's order; none means no connected corpus can hold
    the citation, so it cannot be checked."""

    names: list[str]
    route: Route
    jurisdiction: str | None


def as_code(written: object) -> str | None:
    """A jurisdiction the judge named, as a code; anything else counts as not named."""
    try:
        return code(written) if isinstance(written, str) and written.strip() else None
    except UnknownJurisdiction:
        return None


def covers(listed: list[str], jurisdiction: str) -> bool:
    """A corpus that lists no jurisdiction covers all; one that lists a country covers its
    parts (`US` covers `US-CA`), and one that lists a part covers only that part."""
    return not listed or jurisdiction in listed or jurisdiction.partition("-")[0] in listed


def route(
    corpora: dict[str, CorpusConfig],
    jurisdiction: str | None,
    kind: str | None,
    case_jurisdiction: str | None,
) -> Routing:
    if jurisdiction is not None:
        wanted, how = jurisdiction, Route.CITATION
    elif case_jurisdiction is not None:
        wanted, how = case_jurisdiction, Route.CASE
    else:
        wanted, how = None, Route.ALL
    names = [n for n, c in corpora.items() if wanted is None or covers(c.jurisdictions, wanted)]
    holding = HOLDING.get(kind or "")
    if holding is not None:
        names = [n for n in names if not corpora[n].holds or holding in corpora[n].holds]
    return Routing(names, how, wanted)


def covered(corpora: dict[str, CorpusConfig]) -> list[str] | None:
    """Every code the setup's corpora list, for the judge to choose from; None when a corpus
    covers every jurisdiction, so any code may be named."""
    if any(not c.jurisdictions for c in corpora.values()):
        return None
    return sorted({j for c in corpora.values() for j in c.jurisdictions})
