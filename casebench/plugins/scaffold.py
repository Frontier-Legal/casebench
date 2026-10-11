"""Write a plugin skeleton: a `casebench-<name>` package, or a built-in folder in the core."""

import json
import re
import tomllib
from pathlib import Path

from casebench.plugins.kinds import PluginKind
from casebench.plugins.manifest import MANIFEST_FILE, SAMPLES_DIR
from casebench.plugins.templates import (
    CLASS_NAMES,
    CONFORMANCE_TEST,
    SAMPLES_README,
    STUBS,
)

NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def check_name(name: str) -> None:
    if not NAME.match(name):
        raise ValueError(f"{name!r} must be lowercase letters, digits and underscores")


def _stub(kind: PluginKind, name: str) -> str:
    return STUBS[kind.name].format(name=name, env=name.upper())


def _write(path: Path, text: str) -> None:
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(kind: PluginKind, name: str, obj: str) -> str:
    return json.dumps({"kind": kind.name, "name": name, "object": obj}, indent=2) + "\n"


def new_package(kind: PluginKind, name: str, parent: Path) -> Path:
    """`casebench-<name>/`, installable with `pip install -e`, registering its entry point."""
    check_name(name)
    root = parent / f"casebench-{name}"
    module = f"casebench_{name}"
    obj = f"{module}:{CLASS_NAMES[kind.name]}"
    _write(root / module / "__init__.py", _stub(kind, name))
    _write(root / MANIFEST_FILE, _manifest(kind, name, obj))
    _write(root / SAMPLES_DIR / "README.md", SAMPLES_README)
    _write(root / "tests" / "test_conformance.py", CONFORMANCE_TEST.format(depth=1, subpath=""))
    _write(
        root / "README.md",
        f"# casebench-{name}\n\nA Casebench {kind.name} plugin. "
        f"Check it with `casebench plugin test .`.\n",
    )
    _write(
        root / "pyproject.toml",
        f"""[project]
name = "casebench-{name}"
version = "0.1.0"
description = "A Casebench {kind.name} plugin."
requires-python = ">=3.11"
dependencies = ["casebench"]

[project.entry-points."{kind.group}"]
{name} = "{obj}"

[build-system]
requires = ["uv_build>=0.9.8,<0.13"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = ""
""",
    )
    return root


def register_entry_point(pyproject: Path, group: str, name: str, obj: str) -> None:
    """Add `name = "obj"` to the group's table, creating the table if needed."""
    text = pyproject.read_text(encoding="utf-8")
    existing = tomllib.loads(text).get("project", {}).get("entry-points", {}).get(group, {})
    if name in existing:
        raise ValueError(f"{pyproject} already registers {name!r} in {group}")
    header = f'[project.entry-points."{group}"]'
    line = f'{name} = "{obj}"'
    if header in text:
        text = text.replace(header, f"{header}\n{line}", 1)
    else:
        text = text.rstrip("\n") + f"\n\n{header}\n{line}\n"
    pyproject.write_text(text, encoding="utf-8")


def new_built_in(kind: PluginKind, name: str, core_root: Path) -> Path:
    """A folder inside the core, registered in the core's own entry points."""
    check_name(name)
    pyproject = core_root / "pyproject.toml"
    if not pyproject.is_file():
        raise FileNotFoundError(f"{core_root} has no pyproject.toml; pass the core's root")
    folder = core_root / kind.built_in_root / name
    module = ".".join((*Path(kind.built_in_root).parts, name))
    obj = f"{module}:{CLASS_NAMES[kind.name]}"
    _write(folder / "__init__.py", _stub(kind, name))
    _write(folder / MANIFEST_FILE, _manifest(kind, name, obj))
    _write(folder / SAMPLES_DIR / "README.md", SAMPLES_README)
    subpath = " / " + " / ".join(f'"{part}"' for part in (*Path(kind.built_in_root).parts, name))
    _write(
        core_root / "tests" / "plugins" / f"test_{kind.name}_{name}.py",
        CONFORMANCE_TEST.format(depth=2, subpath=subpath),
    )
    register_entry_point(pyproject, kind.group, name, obj)
    return folder
