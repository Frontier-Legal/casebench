"""Read casebench.yaml."""

import copy
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import Field, StringConstraints, ValidationError, model_validator

from casebench import envfiles
from casebench.capture.config import CaptureConfig
from casebench.core.model import Record
from casebench.corpus.binding import CorpusConfig
from casebench.corpus.guard import refuse_self_check
from casebench.corpus.ids import NAME
from casebench.extract.config import ExtractConfig
from casebench.judge.config import JudgeConfig
from casebench.judge.families import AgentModel
from casebench.network import NetworkConfig

DEFAULT_CONFIG = Path("casebench.yaml")


class ConfigError(ValueError):
    """casebench.yaml is missing or does not validate; the message says where."""


# The name a single `corpus:` is read under (decision 0036).
SINGLE = "corpus"
CorpusName = Annotated[str, StringConstraints(pattern=NAME)]
# A judge and, optionally, a second one from another model family (decision 0035).
MOST_JUDGES = 2


class CloudConfig(Record):
    """The `cloud:` section: the team server `casebench push` and `pull` talk to. Its API key
    is read from `key_env`, in the environment or a .env file, and never written (0059)."""

    url: str
    key_env: str = "CASEBENCH_CLOUD_KEY"


class WorkbenchConfig(Record):
    """The `workbench:` section: what trying a question in the workbench may spend each day,
    in US dollars, the agent's and the judge's model calls together (decision 0052), and
    whether a change to golden data waits for a second editor (decision 0053)."""

    try_daily_limit_usd: float | None = Field(default=None, ge=0)
    second_approval: bool = False


class CasebenchConfig(Record):
    """`corpora:` names every corpus; `corpus:` is the form for one, read as one named
    `corpus`. Likewise `judges:` and `judge:`."""

    target: dict[str, Any] | None = None
    corpora: dict[CorpusName, CorpusConfig] = Field(default_factory=dict)
    capture: CaptureConfig | None = None
    judges: list[JudgeConfig] = Field(default_factory=list, max_length=MOST_JUDGES)
    extract: ExtractConfig | None = None
    agent_models: list[AgentModel] = Field(
        default_factory=list,
        description="Each model the agent calls, with its catalog family, so a run can warn "
        "when a judge shares it (decision 0047).",
    )
    keys: dict[str, str] = Field(
        default_factory=dict,
        description="Each key's variable name and the .env file it is read from, relative to "
        "this file, when the environment does not set it; never a value (decision 0043).",
    )
    network: NetworkConfig | None = None
    workbench: WorkbenchConfig | None = None
    cloud: CloudConfig | None = None

    @property
    def judge(self) -> JudgeConfig | None:
        """The first judge: it lists an answer's citations, and decides alone when it is the
        only one."""
        return self.judges[0] if self.judges else None

    @model_validator(mode="before")
    @classmethod
    def _one_judge_is_a_list_of_one(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "judge" not in data:
            return data
        if data.get("judges"):
            raise ValueError("give `judge:` for one judge or `judges:` for two, not both")
        single = data["judge"]
        rest = {key: value for key, value in data.items() if key != "judge"}
        return {**rest, "judges": [single]} if single is not None else rest

    @model_validator(mode="before")
    @classmethod
    def _one_corpus_is_a_named_one(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "corpus" not in data:
            return data
        if data.get("corpora"):
            raise ValueError("give `corpus:` for one store or `corpora:` for several, not both")
        single = data["corpus"]
        rest = {key: value for key, value in data.items() if key != "corpus"}
        return {**rest, "corpora": {SINGLE: single}} if single is not None else rest

    @model_validator(mode="after")
    def _no_corpus_is_the_target(self) -> "CasebenchConfig":
        for corpus in self.corpora.values():
            refuse_self_check(self.target or {}, corpus)
        return self


def relative_to(base: Path, entry: str) -> str:
    """A `script.py[:function]` entry with a relative path, made relative to the config's
    folder; module entries and absolute paths stay as they are."""
    location, colon, function = entry.rpartition(":")
    if not location or not location.endswith(".py"):
        location, colon, function = entry, "", ""
    if not location.endswith(".py") or Path(location).is_absolute():
        return entry
    return f"{(base / location).resolve()}{colon}{function}"


def load_config(path: Path = DEFAULT_CONFIG) -> CasebenchConfig:
    """`yaml.safe_load` only: a config never constructs Python objects. Script paths in it
    are relative to the config file."""
    if not path.is_file():
        raise ConfigError(f"{path} does not exist; run casebench init or pass --config")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base = path.resolve().parent
    config = config_from(data, base, str(path))
    # Keys the team keeps in .env files are read by name, for every command (decision 0043).
    envfiles.load(config.keys, base)
    return config


def config_from(data: Any, base: Path, where: str) -> CasebenchConfig:
    """The settings as written in a file in `base`, validated as every command reads them;
    `where` names the file in the error."""
    if not isinstance(data, dict):
        raise ConfigError(f"{where}: the file must hold settings by name, such as `judge:`")
    data = copy.deepcopy(data)
    target = data.get("target") or {}
    if isinstance(target.get("entry"), str):
        target["entry"] = relative_to(base, target["entry"])
    if target.get("type") == "python":
        # An adapter under .casebench/ imports the project as its root does (decision 0044).
        target.setdefault("root", str(base))
    for function in (data.get("capture") or {}).get("functions") or []:
        if isinstance(function, dict) and isinstance(function.get("function"), str):
            function["function"] = relative_to(base, function["function"])
    try:
        return CasebenchConfig.model_validate(data)
    except ValidationError as error:
        problems = "; ".join(
            ".".join(str(part) for part in e["loc"]) + ": " + e["msg"].removeprefix("Value error, ")
            if e["loc"]
            else e["msg"].removeprefix("Value error, ")
            for e in error.errors()
        )
        raise ConfigError(f"{where}: {problems}") from error


def target_of(config: CasebenchConfig) -> dict[str, Any]:
    """The target a command needs; a config with none says how to add one."""
    if config.target is None:
        raise ConfigError("the config has no target; add `target:` to casebench.yaml")
    return config.target
