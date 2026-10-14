"""The `report.json` record: one run's tables, citation rates, authority funnel and scores."""

from pydantic import Field

from casebench.core.model import FrozenRecord
from casebench.core.score import Score
from casebench.formats.extensions import Extensions
from casebench.formats.version import FormatVersion
from casebench.report.agreement import JudgeAgreement
from casebench.report.citations import CitationRate
from casebench.report.funnel import CaseFunnel, FunnelSummary
from casebench.report.tables import Table
from casebench.runs.log import ScoringError
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
    suite_id: str | None = None
    suite_hash: str | None = Field(
        default=None,
        description="The hash of the suite the run ran, which changes with any case (0039).",
    )
    produced_by: Producer
    tables: list[Table]
    citations: list[CitationRate]
    agreement: list[JudgeAgreement] = Field(
        default_factory=list, description="Per metric, with two judges (decision 0035)."
    )
    funnel: Funnel
    scores: list[Score]
    scoring_errors: list[ScoringError] = Field(
        default_factory=list,
        description="Results a metric could not score; scoring the run again finishes them "
        "(decision 0037).",
    )
    extensions: Extensions = Field(default_factory=dict)
