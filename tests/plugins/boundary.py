"""Find framework code that reaches into a built-in plugin, by import or by name."""

import ast
import tomllib
from pathlib import Path

from casebench.plugins.kinds import KINDS

NAMED_GROUPS = ("casebench.adapters", "casebench.providers", "casebench.capture")


def _module(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _docstrings(tree: ast.Module) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
            ids.add(id(body[0].value))
    return ids


def plugin_leaks(root: Path) -> list[str]:
    plugin_roots = [".".join(Path(kind.built_in_root).parts) for kind in KINDS]
    entry_points = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    groups = entry_points.get("project", {}).get("entry-points", {})
    names = {name for group in NAMED_GROUPS for name in groups.get(group, {})}

    leaks = []
    for path in sorted((root / "casebench").rglob("*.py")):
        module = _module(root, path)
        if any(module == p or module.startswith(f"{p}.") for p in plugin_roots):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _docstrings(tree)
        for node in ast.walk(tree):
            imported = []
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            for target in imported:
                if any(target == p or target.startswith(f"{p}.") for p in plugin_roots):
                    leaks.append(f"{module} imports {target}")
            if isinstance(node, ast.Constant) and id(node) not in skip and node.value in names:
                leaks.append(f"{module} names the plugin {node.value!r}")
    return leaks
