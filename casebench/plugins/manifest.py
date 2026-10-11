"""The manifest every plugin folder carries, and the entry point it must agree with."""

import importlib
import sys
import tomllib
from pathlib import Path
from typing import Any

from casebench.core.model import Record
from casebench.plugins.kinds import PluginKind, kind_named

MANIFEST_FILE = "casebench-plugin.json"
SAMPLES_DIR = "samples"


class PluginManifest(Record):
    kind: str
    name: str
    object: str

    @property
    def plugin_kind(self) -> PluginKind:
        return kind_named(self.kind)


def read_manifest(folder: Path) -> PluginManifest:
    path = folder / MANIFEST_FILE
    if not path.is_file():
        raise FileNotFoundError(f"{folder} has no {MANIFEST_FILE}")
    return PluginManifest.model_validate_json(path.read_text(encoding="utf-8"))


def find_pyproject(folder: Path) -> Path | None:
    for directory in (folder.resolve(), *folder.resolve().parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def registered_entry_point(folder: Path, manifest: PluginManifest) -> str | None:
    """The object the nearest pyproject.toml registers under the manifest's name."""
    pyproject = find_pyproject(folder)
    if pyproject is None:
        return None
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    group = data.get("project", {}).get("entry-points", {}).get(manifest.plugin_kind.group, {})
    return group.get(manifest.name)


def load_object(folder: Path, manifest: PluginManifest) -> Any:
    """Import the plugin's object, from the folder itself if it is not installed."""
    module_name, _, attribute = manifest.object.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        sys.path.insert(0, str(folder.resolve()))
        module = importlib.import_module(module_name)
    return getattr(module, attribute)
