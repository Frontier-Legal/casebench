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
from casebench.judge.resolve import Resolver, cited_documents
from casebench.metrics.base import Metric
from casebench.metrics.loading import metrics_for
from casebench.report import render
from casebench.report.funnel import CaseFunnel, FunnelSummary, case_funnel, gold, summarise
from casebench.report.tables import Table, build_tables
from casebench.runs.log import RunLog
from casebench.runs.rescore import rescore


@dataclass
class Scored:
    score_set: Path
    scores: list[Score]
    tables: list[Table]
    funnel: FunnelSummary
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


def funnels(log: RunLog, cases: list[Case], context: dict[str, Any]) -> list[CaseFunnel]:
    """Cases whose court authorities resolved to corpus documents; the answer's citations
    are resolved with the run's judge, whose replies the metrics may have kept already."""
    by_id = {case.id: case for case in cases if gold(case)}
    judge: Judge | None = context.get("judge")
    corpus: Corpus | None = context.get("corpus")
    traced = []
    for result in log.results():
        case = by_id.get(result.case_id)
        if case is None:
            continue
        cited = None
        if judge is not None and corpus is not None:
            resolver = Resolver(judge, corpus, context["candidates"])
            output = result.output or ""
            cited = cited_documents(judge, resolver, output) if output else {}
        traced.append(case_funnel(case, result, cited))
    return traced


def score(log: RunLog, cases: list[Case], config: CasebenchConfig, suite_id: str) -> Scored:
    """The judge's replies are kept in the run folder; scoring again reads them back."""
    context = context_for(config, Memo(log.folder / MEMO_FILE))
    path = rescore(log, cases, metrics_for(cases, context))
    scores = RunLog.read_scores(path)
    tables = build_tables(scores, cases, suite_id)
    traced = funnels(log, cases, context)
    summary = summarise(traced)
    report = render.write(log.folder, tables, scores, path, traced, summary)
    return Scored(path, scores, tables, summary, report)
