"""Find the variable that holds a key, in the shell or a .env file, asking only if unsure."""

import os
from dataclasses import dataclass
from pathlib import Path

from casebench import envfiles
from casebench.setup.picker import pick, text

SHELL = "\0shell"
NONE = "\0none"


@dataclass(frozen=True)
class KeyFound:
    """`file` is None when the shell sets the variable."""

    name: str
    file: Path | None

    def said(self, root: Path) -> str:
        if self.file is None:
            return f"{self.name}, set in this shell"
        return f"{self.name} in {self.file.relative_to(root).as_posix()}"


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_of(name: str, root: Path, label: str) -> Path | None:
    """The file to read `name` from, when several hold it and do not agree."""
    holding = [(p, envfiles.value(p, name)) for p in envfiles.env_files(root)]
    holding = [(p, v) for p, v in holding if v]
    if not holding:
        return None
    if len({v for _, v in holding}) == 1:
        return holding[0][0]
    choices = [(f"{_relative(p, root)}  ({envfiles.masked(v or '')})", str(p)) for p, v in holding]
    return Path(pick(f"{label}: {name} has different values in these files; which one?", choices))


def _chosen(root: Path, label: str, expected: str | None) -> KeyFound | None:
    """No file holds the expected name, or there is none: the file, then the name in it."""
    files = envfiles.env_files(root)
    choices = [(f"{_relative(p, root)}  ({len(envfiles.names(p))} names)", str(p)) for p in files]
    choices += [("it is set in my shell", SHELL), ("no key is needed", NONE)]
    where = pick(f"{label}: which .env file holds its key?", choices)
    if where == NONE:
        return None
    if where == SHELL:
        return KeyFound(text(f"{label}: the variable's name", default=expected), None)
    path = Path(where)
    held = envfiles.names(path)
    if not held:
        return None
    # Only the exact name the config expects is preselected; nothing is guessed from words.
    preselected = expected if expected in held else None
    asked = f"{label}: which key in {_relative(path, root)}?"
    name = pick(asked, [(n, n) for n in held], preselected)
    return KeyFound(name, path)


def use(found: KeyFound) -> None:
    """Set a key read from a file for this run, so a live check can use it now."""
    if found.file is not None and not os.environ.get(found.name):
        os.environ[found.name] = envfiles.value(found.file, found.name) or ""


def key_for(expected: str | None, root: Path, label: str) -> KeyFound | None:
    """The expected variable from the shell or the one .env file that holds it, with no
    question; a choice only when files disagree or none holds it. Values are never shown,
    except masked to tell two apart (decision 0043)."""
    if expected and os.environ.get(expected):
        return KeyFound(expected, None)
    if expected and (file := _file_of(expected, root, label)) is not None:
        return KeyFound(expected, file)
    return _chosen(root, label, expected)
