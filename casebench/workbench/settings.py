"""casebench.yaml as the workbench's Settings page reads it and saves it, one section at a time.

A save is validated as every command reads the file, and changes nothing when it does not
validate; the workbench then serves the saved settings without restarting (decision 0063).
"""

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from casebench.config import SINGLE, CasebenchConfig, ConfigError, config_from, load_config
from casebench.judge.judges import shared_family
from casebench.pricing.lookup import PriceList, lookup
from casebench.pricing.lookup import saved as saved_prices
from casebench.pricing.priced import priced
from casebench.setup.config_schema import LINE, write_schema

# Each section the page edits, in the order a new file lists them.
SECTIONS = (
    "target",
    "agent_models",
    "corpora",
    "judges",
    "extract",
    "capture",
    "network",
    "workbench",
    "cloud",
    "keys",
)
# The forms a file may use for one judge or one corpus, read as the lists above.
SHORT_FORMS = {"judge": "judges", "corpus": "corpora"}


class Refused(ValueError):
    """The settings were not saved; the message says why."""


def header() -> str:
    """The lines `casebench init` starts the file with, kept on every save (decision 0042)."""
    from casebench.setup.init_cli import HEADER

    return HEADER


def as_sections(data: dict[str, Any]) -> dict[str, Any]:
    """The file's settings with `judge:` read as `judges:` and `corpus:` as `corpora:`."""
    out = dict(data)
    if "judge" in out:
        single = out.pop("judge")
        out["judges"] = [single] if single is not None else []
    if "corpus" in out:
        single = out.pop("corpus")
        out["corpora"] = {SINGLE: single} if single is not None else {}
    return out


def as_written(sections: dict[str, Any]) -> dict[str, Any]:
    """Sections in the forms `casebench init` writes: one judge as `judge:`, one corpus named
    `corpus` as `corpus:`; an empty section is left out."""
    out: dict[str, Any] = {}
    for name, value in sections.items():
        if value is None or value == {} or value == []:
            continue
        if name == "judges" and len(value) == 1:
            out["judge"] = value[0]
        elif name == "corpora" and list(value) == [SINGLE]:
            out["corpus"] = value[SINGLE]
        else:
            out[name] = value
    return out


class Settings:
    """The settings the workbench serves, read from `path` when there is one. `changed` is
    told each time a save takes effect."""

    def __init__(
        self,
        path: Path | None,
        config: CasebenchConfig | None = None,
        changed: Callable[[CasebenchConfig | None], None] | None = None,
    ) -> None:
        self.path = path
        self.config = config
        self.changed = changed
        # The sellers' price lists, which price every model the file does not (decision 0069).
        self.prices = PriceList()

    @property
    def editable(self) -> bool:
        return self.path is not None

    def text(self) -> str:
        if self.path is None or not self.path.is_file():
            return ""
        return self.path.read_text(encoding="utf-8")

    def sections(self) -> dict[str, Any]:
        """Every section as the file writes it, unresolved: paths stay relative."""
        data = yaml.safe_load(self.text()) or {}
        return as_sections(data) if isinstance(data, dict) else {}

    def has_comments(self) -> bool:
        """Whether a save would drop comments: any besides the header's (decision 0042)."""
        body = self.text().removeprefix(header()).removeprefix(LINE)
        return any(line.lstrip().startswith("#") for line in body.splitlines())

    def save_section(self, name: str, value: Any) -> None:
        if name not in SECTIONS:
            raise Refused(f"there is no section {name!r}; the sections are {', '.join(SECTIONS)}")
        sections = {**self.sections(), name: value}
        # In the order a new file lists them; a name no section has is kept, and refused.
        ordered = {key: sections.get(key) for key in SECTIONS} | sections
        self._write(as_written(ordered))

    def save_text(self, text: str) -> None:
        """The whole file as the engineer wrote it, header and comments included."""
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as error:
            raise Refused(f"the file is not YAML: {error}") from None
        self._check(data)
        self._replace(text)

    def _check(self, data: Any) -> None:
        path = self._path()
        try:
            config = config_from(data, path.resolve().parent, str(path.name))
        except ConfigError as error:
            raise Refused(str(error)) from None
        shared = shared_family(config.judges)
        if shared:
            # A run refuses it too; saving it would only put the refusal off (decision 0035).
            raise Refused(
                f"both judges are of the {shared} family; pick a second judge from another "
                "model family, or keep one judge"
            )

    def _write(self, data: dict[str, Any]) -> None:
        self._check(data)
        self._replace(header() + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    def _replace(self, text: str) -> None:
        """Write next to the file and move it into place, so a reader never sees half."""
        path = self._path()
        written = path.with_name(f".{path.name}.saving")
        written.write_text(text, encoding="utf-8")
        written.replace(path)
        if text.startswith(LINE):
            # The schema an editor reads is this version's (decision 0061).
            write_schema(path.resolve().parent)
        self.reload()

    def reload(self) -> None:
        path = self._path()
        self.config = priced(load_config(path), self.prices) if path.is_file() else None
        if self.changed is not None:
            self.changed(self.config)

    def look_up_prices(self) -> None:
        """The last lists at once, then fresh ones in the background; each takes effect as it
        arrives, without a restart."""
        self.prices = saved_prices()
        if self.path is not None and self.path.is_file():
            self.reload()

        def fresh() -> None:
            self.prices = lookup()
            if self.path is not None and self.path.is_file():
                self.reload()

        threading.Thread(target=fresh, daemon=True).start()

    def _path(self) -> Path:
        if self.path is None:
            raise Refused("this workbench reads no casebench.yaml, so its settings cannot change")
        return self.path
