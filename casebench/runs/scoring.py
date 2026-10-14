"""Score a finished run with the metrics its cases name, and write its report."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casebench.config import CasebenchConfig
from casebench.core.case import Case
from casebench.core.score import Score
from casebench.corpus.cache import corpus_key
from casebench.corpus.corpora import Corpora
from casebench.judge.client import Judge
from casebench.judge.judges import judges_for
from casebench.judge.memo import MEMO_FILE, Memo
from casebench.judge.resolve import Resolver, cited_documents
from casebench.metrics.base import Metric
from casebench.metrics.loading import metrics_for
from casebench.report import render
from casebench.report.funnel import CaseFunnel, FunnelSummary, case_funnel, gold, summarise
from casebench.report.tables import Table, build_tables
from casebench.runs.log import RunLog
from casebench.runs.producer import JudgeUsed, Producer, producer_for
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
    if config.judges:
        first, *second = judges_for(config.judges, memo)
        context["judge"] = first
        context["second_judge"] = second[0] if second else None
        context["candidates"] = first.config.candidates
    if config.corpora:
        context["corpus"] = Corpora(config.corpora)
    return context


def prepare(cases: list[Case], config: CasebenchConfig) -> list[Metric]:
    """Built before anything is sent, so a metric missing its judge or corpus stops the run."""
    return metrics_for(cases, context_for(config))


def funnels(log: RunLog, cases: list[Case], context: dict[str, Any]) -> list[CaseFunnel]:
    """Cases whose court authorities resolved to corpus documents; the answer's citations
    are resolved with the run's judge, whose replies the metrics may have kept already."""
    by_id = {case.id: case for case in cases if gold(case)}
    judge: Judge | None = context.get("judge")
    corpus: Corpora | None = context.get("corpus")
    traced = []
    for result in log.results():
        case = by_id.get(result.case_id)
        if case is None:
            continue
        cited = None
        if judge is not None and corpus is not None:
            resolver = Resolver(judge, corpus, context["candidates"])
            output = result.output or ""
            place = case.provenance.jurisdiction if case.provenance else None
            cited = cited_documents(resolver, output, place) if output else {}
        traced.append(case_funnel(case, result, cited))
    return traced


def producer(
    metrics: list[Metric], cases: list[Case], config: CasebenchConfig, context: dict[str, Any]
) -> Producer:
    """A judge's family comes from its provider, which is why the built judges are read."""
    judges = [
        JudgeUsed(
            provider=judge.config.provider,
            model=judge.config.model,
            family=judge.family,
            candidates=judge.config.candidates,
        )
        for judge in (context.get("judge"), context.get("second_judge"))
        if judge is not None
    ]
    corpora = {name: corpus_key(c.connector, c.options) for name, c in config.corpora.items()}
    return producer_for(metrics, cases, judges, corpora)


def score(log: RunLog, cases: list[Case], config: CasebenchConfig, suite_id: str) -> Scored:
    """The judge's replies are kept in the run folder; scoring again reads them back."""
    context = context_for(config, Memo(log.folder / MEMO_FILE))
    metrics = metrics_for(cases, context)
    produced_by = producer(metrics, cases, config, context)
    path = rescore(log, cases, metrics, produced_by)
    scores = RunLog.read_scores(path)
    tables = build_tables(scores, cases, suite_id)
    traced = funnels(log, cases, context)
    summary = summarise(traced)
    report = render.write(log.folder, produced_by, tables, scores, path, traced, summary)
    return Scored(path, scores, tables, summary, report)
