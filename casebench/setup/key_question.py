"""Find the variable that holds a key, in the shell or a .env file, asking only if unsure."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import click

from casebench import envfiles, keys
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


# Where a script said each key is read from, with --key NAME=FILE (decision 0044).
_given: dict[str, Path] = {}


def preset(given: Mapping[str, Path]) -> None:
    """Take the files a script named for its keys, so no question is asked about them."""
    _given.clear()
    _given.update(given)


def given_keys(pairs: tuple[str, ...], root: Path) -> dict[str, Path]:
    """`NAME=FILE` pairs, each file relative to the root and holding that name."""
    found: dict[str, Path] = {}
    for pair in pairs:
        name, sep, file = pair.partition("=")
        path = (root / file).resolve()
        if not sep or not name:
            raise click.BadParameter(f"{pair!r} must look like NAME=FILE", param_hint="--key")
        if envfiles.value(path, name) is None:
            raise click.BadParameter(f"{file} gives {name} no value", param_hint="--key")
        found[name] = path
    return found


def located(name: str, root: Path) -> Path | None:
    """The file to read `name` from: the one a script named, or the only value the project's
    .env files give it. None when no file has it. Files that disagree are a choice for a
    person at a terminal; without one, the files and the flag that settles it are named."""
    if name in _given:
        return _given[name]
    holding = envfiles.holders(name, root)
    if len(set(holding.values())) <= 1:
        return next(iter(holding), None)
    choices = [
        (f"{_relative(p, root)}  (fingerprint {keys.fingerprint(v)})", str(p))
        for p, v in holding.items()
    ]
    asked = f"{name} has different values in these files; which one?"
    return Path(pick(asked, choices, flag=f"--key {name}=FILE"))


def _chosen(root: Path, label: str, expected: str | None) -> KeyFound | None:
    """No file holds the expected name, or there is none: the file, then the name in it."""
    files = envfiles.env_files(root)
    choices = [(f"{_relative(p, root)}  ({len(envfiles.names(p))} names)", str(p)) for p in files]
    choices += [("it is set in my shell", SHELL), ("no key is needed", NONE)]
    flag = f"--key {expected}=FILE" if expected else None
    where = pick(f"{label}: which .env file holds its key?", choices, flag=flag)
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


def hold_located(names: set[str], root: Path) -> dict[str, str]:
    """Each named key the shell lacks, located in the project's .env files and held for this
    run's own calls; returns each one's file, relative to the root, for `keys` (0044)."""
    found: dict[str, str] = {}
    for name in sorted(names):
        if os.environ.get(name):
            continue
        path = located(name, root)
        if path is not None:
            keys.hold(name, envfiles.value(path, name) or "")
            found[name] = _relative(path, root)
    return found


def use(found: KeyFound) -> None:
    """Hold a key read from a file for this run's own calls, so a live check can use it now;
    it is not set in the environment."""
    if found.file is not None and not os.environ.get(found.name):
        keys.hold(found.name, envfiles.value(found.file, found.name) or "")


def key_for(expected: str | None, root: Path, label: str) -> KeyFound | None:
    """The expected variable from the shell or the one .env file that holds it, with no
    question; a choice only when files disagree or none holds it. No value is shown, only a
    fingerprint to tell two apart (decision 0043)."""
    if expected and os.environ.get(expected):
        return KeyFound(expected, None)
    if expected and (file := located(expected, root)) is not None:
        return KeyFound(expected, file)
    return _chosen(root, label, expected)
