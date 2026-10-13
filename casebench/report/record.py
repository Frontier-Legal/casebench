"""The `report.json` record: one run's tables, citation rates, authority funnel and scores."""

from pydantic import Field

from casebench.core.model import FrozenRecord
from casebench.core.score import Score
from casebench.formats.extensions import Extensions
from casebench.formats.version import FormatVersion
from casebench.report.citations import CitationRate
from casebench.report.funnel import CaseFunnel, FunnelSummary
from casebench.report.tables import Table
from casebench.runs.producer import Producer

FORMAT = FormatVersion("report", 1, 0)


class Funnel(FrozenRecord):
    """How many gold authorities survived each step, over the run and per case."""

    summary: FunnelSummary
    cases: list[CaseFunnel]


class Report(FrozenRecord):
    """One scored run: a table per task and metric, never one overall figure (rule 8)."""

    format: str = Field(pattern=FORMAT.pattern)
    score_set: str
    produced_by: Producer
    tables: list[Table]
    citations: list[CitationRate]
    funnel: Funnel
    scores: list[Score]
    extensions: Extensions = Field(default_factory=dict)
