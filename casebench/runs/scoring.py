"""Score a finished run with the metrics its cases name, and write its report."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casebench.capture.step import StepKind
from casebench.config import CasebenchConfig
from casebench.core.case import Case
from casebench.core.score import Score
from casebench.corpus.cache import corpus_key
from casebench.corpus.corpora import Corpora
from casebench.judge.client import Judge
from casebench.judge.families import family_warnings
from casebench.judge.judges import judges_for
from casebench.judge.memo import MEMO_FILE, Memo
from casebench.judge.resolve import Resolver, cited_documents
from casebench.metrics.base import Metric
from casebench.metrics.loading import metrics_for
from casebench.report import render
from casebench.report.calibration import lawyers_win, read_reviews
from casebench.report.funnel import CaseFunnel, FunnelSummary, case_funnel, gold, summarise
from casebench.report.tables import Table, build_tables
from casebench.runs.log import RunLog, ScoringError
from casebench.runs.producer import JudgeUsed, Producer, producer_for
from casebench.runs.rescore import evidenced, rescore


@dataclass
class Scored:
    score_set: Path
    scores: list[Score]
    tables: list[Table]
    funnel: FunnelSummary
    report: Path
    errors: list[ScoringError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unevidenced: list[str] = field(default_factory=list)


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


FUNNEL = "authority funnel"


def funnels(
    log: RunLog, cases: list[Case], context: dict[str, Any], errors: list[ScoringError]
) -> tuple[list[CaseFunnel], list[ScoringError]]:
    """Cases whose court authorities resolved to corpus documents; the answer's citations
    are resolved with the run's judge, whose replies the metrics may have kept already. A
    case a metric could not score is left out, and so is one whose citations cannot be
    resolved now, with its error (decision 0037)."""
    by_id = {case.id: case for case in cases if gold(case)}
    unscored = {(e.case_id, e.repeat) for e in errors}
    judge: Judge | None = context.get("judge")
    corpus: Corpora | None = context.get("corpus")
    traced, failed = [], []
    for result in log.results():
        case = by_id.get(result.case_id)
        if case is None or (result.case_id, result.repeat) in unscored:
            continue
        cited = None
        if judge is not None and corpus is not None:
            resolver = Resolver(judge, corpus, context["candidates"])
            output = result.output or ""
            place = case.provenance.jurisdiction if case.provenance else None
            try:
                cited = cited_documents(resolver, output, place) if output else {}
            except Exception as failure:
                error = f"{type(failure).__name__}: {failure}"
                failed.append(
                    ScoringError(case_id=case.id, repeat=result.repeat, metric=FUNNEL, error=error)
                )
                continue
        traced.append(case_funnel(case, result, cited))
    return traced, failed


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


def judge_cost(context: dict[str, Any]) -> float | None:
    """What the judges' calls have cost so far, or None when one has no price (0038)."""
    judges = [j for j in (context.get("judge"), context.get("second_judge")) if j is not None]
    costs = [judge.cost for judge in judges]
    return None if None in costs else sum(c for c in costs if c is not None)


def score(
    log: RunLog,
    cases: list[Case],
    config: CasebenchConfig,
    suite_id: str,
    concurrency: int = 1,
    on_scored: Callable[[str, float, float | None], None] | None = None,
) -> Scored:
    """The judge's replies are kept in the run folder; scoring again reads them back, so it
    asks only what failed before. Up to `concurrency` cases are scored at once (0037).
    `on_scored` hears of each case scored, its time and the judges' cost so far (0038)."""
    context = context_for(config, Memo(log.folder / MEMO_FILE))
    metrics = metrics_for(cases, context)
    produced_by = producer(metrics, cases, config, context)

    def heard(case_id: str, seconds: float) -> None:
        if on_scored is not None:
            on_scored(case_id, seconds, judge_cost(context))

    path = rescore(log, cases, metrics, produced_by, concurrency, heard)
    # The score set keeps the judge's verdicts; lawyers' replace them in the report (0047).
    scores = lawyers_win(RunLog.read_scores(path), read_reviews(log.folder))
    errors = RunLog.read_errors(path)
    tables = build_tables(scores, cases, suite_id)
    traced, unfunnelled = funnels(log, cases, context, errors)
    errors += unfunnelled
    summary = summarise(traced)
    judges = [(f"{j.provider}/{j.model}", j.family) for j in produced_by.judges]
    called = {
        step.model
        for result in log.results()
        for step in result.steps
        if step.kind is StepKind.LLM and step.model
    }
    warnings = family_warnings(judges, config.agent_models, called)
    unevidenced = [case.id for case in cases if not evidenced(case, metrics)]
    report = render.write(
        log.folder,
        produced_by,
        tables,
        scores,
        path,
        traced,
        summary,
        errors,
        (log.info.suite_id, log.info.suite_hash),
        warnings,
        unevidenced,
    )
    return Scored(path, scores, tables, summary, report, errors, warnings, unevidenced)
