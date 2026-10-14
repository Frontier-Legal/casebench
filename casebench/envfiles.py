"""Find a project's .env files and read named variables from them, never anything else."""

import os
from pathlib import Path

from casebench.keys import hold

# Folders that hold no file of the project's own.
SKIPPED = {"node_modules", "__pycache__", "site-packages"}
# A file of placeholders that documents the variables, not one that holds them.
EXAMPLES = (".example", ".sample", ".template", ".dist")


def is_env_file(name: str) -> bool:
    """`.env`, `.env.<anything>` or `<anything>.env`, and not a file of placeholders."""
    named = name == ".env" or name.startswith(".env.") or name.endswith(".env")
    return named and not name.endswith(EXAMPLES)


def env_files(root: Path) -> list[Path]:
    """Every .env file below the root, outside virtual environments, `node_modules` and
    hidden folders, nearest the root first (decision 0043)."""
    found = []
    for folder, folders, files in os.walk(root):
        here = Path(folder)
        folders[:] = sorted(
            name
            for name in folders
            if not name.startswith(".")
            and name not in SKIPPED
            and not (here / name / "pyvenv.cfg").is_file()
        )
        for name in sorted(files):
            if is_env_file(name):
                found.append(here / name)
    return sorted(found, key=lambda path: (len(path.relative_to(root).parts), str(path)))


def _value(raw: str) -> str:
    raw = raw.strip()
    if raw[:1] in ("'", '"') and raw[-1:] == raw[:1] and len(raw) > 1:
        return raw[1:-1]
    return raw.split(" #", 1)[0].strip()


def _lines(path: Path) -> list[tuple[str, str]]:
    """Each `NAME=value` line, with `export ` and quotes taken off."""
    pairs = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, raw = line.removeprefix("export ").partition("=")
        if name.strip():
            pairs.append((name.strip(), raw))
    return pairs


def names(path: Path) -> list[str]:
    """The variables a file sets, by name; their values are not read."""
    return [name for name, _ in _lines(path)]


def value(path: Path, name: str) -> str | None:
    """One variable's value, the last it is given; the only way a value is read."""
    found = None
    for found_name, raw in _lines(path):
        if found_name == name:
            found = _value(raw)
    return found or None


def load(keys: dict[str, str], base: Path) -> list[str]:
    """Each named variable the shell lacks, read from the file the config names for it,
    relative to the config's folder, and held for Casebench's own calls, not set in the
    environment. Returns the names that could not be found."""
    missing = []
    for name, file in keys.items():
        if os.environ.get(name):
            continue
        path = base / file
        found = value(path, name) if path.is_file() else None
        if found is None:
            missing.append(name)
        else:
            hold(name, found)
    return missing
