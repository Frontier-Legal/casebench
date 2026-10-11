"""Name the model SDKs a project depends on, from its dependency files and the parsers' lists."""

import json
import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


def _requirement_names(lines: list[str]) -> set[str]:
    names = set()
    for line in lines:
        try:
            names.add(canonicalize_name(Requirement(line).name))
        except InvalidRequirement:
            continue
    return names


def _pyproject(path: Path) -> set[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    lines = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        lines += extra
    for group in data.get("dependency-groups", {}).values():
        lines += [item for item in group if isinstance(item, str)]
    return _requirement_names(lines)


def _uv_lock(path: Path) -> set[str]:
    """Every package the lock resolves, a workspace's members' dependencies included."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {canonicalize_name(package["name"]) for package in data.get("package", [])}


def _requirements_txt(path: Path) -> set[str]:
    lines = [line.split("#", 1)[0].strip() for line in path.read_text("utf-8").splitlines()]
    return _requirement_names([line for line in lines if line and not line.startswith("-")])


def _package_json(path: Path) -> set[str]:
    """An agent written for Node: the proxy captures its calls like a Python agent's."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {name for key in ("dependencies", "devDependencies") for name in data.get(key, {})}


READERS = {
    "uv.lock": _uv_lock,
    "pyproject.toml": _pyproject,
    "requirements.txt": _requirements_txt,
    "package.json": _package_json,
}


def packages(checkout: Path) -> set[str]:
    found: set[str] = set()
    for name, read in READERS.items():
        if (checkout / name).is_file():
            found |= {canonicalize_name(package) for package in read(checkout / name)}
    return found


def detect(checkout: Path) -> dict[str, str]:
    """Each SDK the project depends on that an installed parser reads, with that parser."""
    found = packages(checkout)
    readers: dict[str, str] = {}
    for parser in registry.available(kind_named("parser")):
        for package in getattr(registry.load(kind_named("parser"), parser.name), "packages", []):
            if canonicalize_name(package) in found:
                readers[package] = parser.name
    return dict(sorted(readers.items()))
