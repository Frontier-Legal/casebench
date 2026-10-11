"""Score a finished run with the metrics its cases name, and write its report."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casebench.config import CasebenchConfig
from casebench.core.case import Case
from casebench.core.score import Score
from casebench.corpus.binding import Corpus
from casebench.judge.client import Judge
from casebench.judge.memo import MEMO_FILE, Memo
from casebench.metrics.base import Metric
from casebench.metrics.loading import metrics_for
from casebench.report import render
from casebench.report.tables import Table, build_tables
from casebench.runs.log import RunLog
from casebench.runs.rescore import rescore


@dataclass
class Scored:
    score_set: Path
    scores: list[Score]
    tables: list[Table]
    report: Path


def context_for(config: CasebenchConfig, memo: Memo | None = None) -> dict[str, Any]:
    """What metrics may ask for: the judge and the corpus, when the config has them."""
    context: dict[str, Any] = {}
    if config.judge is not None:
        context["judge"] = Judge(config.judge, memo=memo)
        context["candidates"] = config.judge.candidates
    if config.corpus is not None:
        context["corpus"] = Corpus(config.corpus)
    return context


def prepare(cases: list[Case], config: CasebenchConfig) -> list[Metric]:
    """Built before anything is sent, so a metric missing its judge or corpus stops the run."""
    return metrics_for(cases, context_for(config))


def score(log: RunLog, cases: list[Case], config: CasebenchConfig, suite_id: str) -> Scored:
    """The judge's replies are kept in the run folder; scoring again reads them back."""
    metrics = metrics_for(cases, context_for(config, Memo(log.folder / MEMO_FILE)))
    path = rescore(log, cases, metrics)
    scores = RunLog.read_scores(path)
    tables = build_tables(scores, cases, suite_id)
    return Scored(path, scores, tables, render.write(log.folder, tables, scores, path))
