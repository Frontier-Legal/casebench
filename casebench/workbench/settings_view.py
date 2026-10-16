"""What the Settings page shows of the setup, and never a key's value.

Each model with what it is for and costs, each key with where it is read from, and what
trying questions and recent runs spent (decision 0063).
"""

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from casebench import keys
from casebench.config import CasebenchConfig, ConfigError, config_from
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.providers.settings import settings_of
from casebench.targets.placeholders import VARIABLE
from casebench.workbench import trying
from casebench.workbench.settings import Settings
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store

# Recent runs, newest first: enough to see what a run costs without reading every folder.
RECENT_RUNS = 10
REPORT_FILE = "report.json"


class ModelView(BaseModel):
    role: str = Field(description="judge, second judge, or extraction model 1 or 2.")
    used_for: str
    provider: str
    model: str
    family: str | None
    max_tokens: int | None
    context_window: int | None
    price_input: float | None = Field(description="US dollars per million input tokens.")
    price_output: float | None = Field(description="US dollars per million output tokens.")
    settings: dict[str, Any]
    key: str | None
    base_url: str | None


class KeyView(BaseModel):
    """`where` says whether a value is found, never what it is."""

    name: str
    where: Literal["shell", "file", "missing"]
    file: str | None
    used_by: list[str]


class RunSpend(BaseModel):
    run_id: str
    suite_id: str
    scored: bool
    agent: float | None
    judge: float | None
    total: float | None
    unpriced: list[str] = Field(default_factory=list)


class Plugins(BaseModel):
    targets: list[str]
    connectors: list[str]
    providers: list[str]


class SettingsView(BaseModel):
    file: str | None
    exists: bool
    editable: bool
    problem: str | None = Field(description="Why the file does not validate, when it does not.")
    has_comments: bool
    sections: dict[str, Any]
    text: str
    models: list[ModelView]
    keys: list[KeyView]
    budget: trying.Budget | None
    runs: list[RunSpend]
    plugins: Plugins


USED_FOR = {
    "judge": "Lists each answer's citations, matches them to the corpus and checks what they "
    "claim; grades criteria",
    "second judge": "Judges every answer again, from another model family, so disagreements show",
    "extraction": "Reads court decisions and writes answer keys, with the other extraction model",
}


def _provider(model: JudgeConfig) -> Any:
    try:
        return Judge(model).provider
    except Exception:
        return None


def _model(role: str, used_for: str, model: JudgeConfig) -> ModelView:
    provider = _provider(model)
    options = model.options
    return ModelView(
        role=role,
        used_for=used_for,
        provider=model.provider,
        model=model.model,
        family=options.get("family") or getattr(provider, "family", None),
        max_tokens=options.get("max_tokens") or getattr(provider, "max_tokens", None),
        context_window=model.context_window,
        price_input=model.price.input if model.price else None,
        price_output=model.price.output if model.price else None,
        settings=settings_of(options),
        key=options.get("api_key_env") or getattr(provider, "api_key_env", None),
        base_url=options.get("base_url") or getattr(provider, "base_url", None),
    )


def models(config: CasebenchConfig) -> list[ModelView]:
    found = []
    for number, judge in enumerate(config.judges):
        role = "judge" if number == 0 else "second judge"
        found.append(_model(role, USED_FOR[role], judge))
    for number, model in enumerate(config.extract.models if config.extract else [], start=1):
        found.append(_model(f"extraction model {number}", USED_FOR["extraction"], model))
    return found


def _named_in(value: Any) -> list[str]:
    """Every `${NAME}` in a section's settings."""
    return VARIABLE.findall(json.dumps(value)) if value else []


def key_views(config: CasebenchConfig) -> list[KeyView]:
    """Each key the settings use, with what uses it, and each one `keys:` names."""
    used: dict[str, list[str]] = {}
    for view in models(config):
        if view.key:
            used.setdefault(view.key, []).append(view.role)
    for name in _named_in(config.target):
        used.setdefault(name, []).append("agent")
    for corpus_name, corpus in config.corpora.items():
        for name in _named_in(corpus.options):
            used.setdefault(name, []).append(f"corpus {corpus_name}")
    for route in config.capture.routes if config.capture else []:
        for name in _named_in(route):
            used.setdefault(name, []).append("capture")
    if config.cloud is not None:
        used.setdefault(config.cloud.key_env, []).append("team server")
    for name in config.keys:
        used.setdefault(name, [])
    views = []
    for name in sorted(used):
        if os.environ.get(name):
            where = "shell"
        elif keys.get(name):
            where = "file"
        else:
            where = "missing"
        views.append(
            KeyView(name=name, where=where, file=config.keys.get(name), used_by=used[name])
        )
    return views


def _spend(folder: Path) -> dict[str, Any] | None:
    try:
        report = json.loads((folder / REPORT_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    spend = report.get("spend")
    return spend if isinstance(spend, dict) else None


def run_spends(workspace: Workspace) -> list[RunSpend]:
    found = []
    for log in list(reversed(workspace.runs()))[:RECENT_RUNS]:
        spend = _spend(log.folder) or {}
        found.append(
            RunSpend(
                run_id=log.info.run_id,
                suite_id=log.info.suite_id,
                scored=bool(log.score_sets()),
                agent=spend.get("agent"),
                judge=spend.get("judge"),
                total=spend.get("total"),
                unpriced=spend.get("unpriced") or [],
            )
        )
    return found


def plugins() -> Plugins:
    def names(kind: str) -> list[str]:
        return sorted({item.name for item in registry.available(kind_named(kind))})

    return Plugins(
        targets=names("target"), connectors=names("connector"), providers=names("provider")
    )


def view(settings: Settings, workspace: Workspace, store: Store, person: str) -> SettingsView:
    sections = settings.sections()
    problem = None
    config = settings.config
    if settings.path is not None and settings.path.is_file():
        try:
            config_from(sections, settings.path.resolve().parent, settings.path.name)
        except ConfigError as error:
            problem = keys.scrub(str(error))
    shown = config or CasebenchConfig()
    names = [view.name for view in key_views(shown)]
    return SettingsView(
        file=str(settings.path) if settings.path else None,
        exists=bool(settings.path and settings.path.is_file()),
        editable=settings.editable,
        problem=problem,
        has_comments=settings.has_comments(),
        # A key written into the file by hand is shown as the variable that holds it.
        sections=json.loads(keys.scrub(json.dumps(sections, default=str), names)),
        text=keys.scrub(settings.text(), names),
        models=models(shown),
        keys=key_views(shown),
        budget=trying.budget(config, store, person) if config else None,
        runs=run_spends(workspace),
        plugins=plugins(),
    )
