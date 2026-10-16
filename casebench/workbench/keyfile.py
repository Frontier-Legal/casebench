"""Write a key typed into the workbench to a .env file git ignores, and nowhere else (0063).

The value is never returned or shown; the workbench holds it for its own calls at once, as a
key read from a file is held (decision 0043).
"""

import os
import re
import subprocess
from pathlib import Path

from casebench import keys

# Where a key goes when `keys:` names no file git ignores; `.casebench/.gitignore` keeps
# everything in that folder out of git but the files it lists.
DEFAULT_FILE = Path(".casebench") / ".env"
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Characters that need the value quoted for envfiles to read it back whole.
NEEDS_QUOTES = re.compile(r"[\s#'\"]")
# Only the owner reads or writes the file.
PRIVATE = 0o600
GITIGNORE = "*\n!.gitignore\n!target.py\n!casebench.schema.json\n"


class Refused(ValueError):
    """The key was not written; the message says why."""


def ignored(path: Path) -> bool:
    """Whether git keeps the file out of commits; a folder git does not track counts as so."""
    folder = next(parent for parent in path.parents if parent.is_dir())
    try:
        found = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", str(path)],
            cwd=folder,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return True
    # 0: ignored; 1: not ignored; 128: not inside a repository.
    return found.returncode != 1


def _line(name: str, value: str) -> str:
    if NEEDS_QUOTES.search(value):
        if '"' in value:
            raise Refused("a key with a double quote in it cannot be written to a .env file")
        return f'{name}="{value}"'
    return f"{name}={value}"


def where_to(name: str, named: dict[str, str], base: Path) -> Path:
    """The file `keys:` names for the key when git ignores it, else `.casebench/.env`."""
    file = named.get(name)
    if file and ignored(base / file):
        return base / file
    return base / DEFAULT_FILE


def write(name: str, value: str, named: dict[str, str], base: Path) -> str:
    """Set the key in its file, replacing any line that set it before; returns the file,
    relative to `base`, for `keys:`."""
    if not NAME.match(name):
        raise Refused(f"{name!r} is not a variable name")
    value = value.strip()
    if not value or "\n" in value or "\r" in value:
        raise Refused("give the key on one line")
    path = where_to(name, named, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent == base / DEFAULT_FILE.parent and not (path.parent / ".gitignore").exists():
        (path.parent / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    if not ignored(path):
        shown = path.relative_to(base)
        raise Refused(f"git does not ignore {shown}, so a key there could be committed")
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    kept = [
        line
        for line in lines
        if line.strip().removeprefix("export ").partition("=")[0].strip() != name
    ]
    path.write_text("\n".join([*kept, _line(name, value)]) + "\n", encoding="utf-8")
    os.chmod(path, PRIVATE)
    keys.hold(name, value)
    return path.relative_to(base).as_posix()
