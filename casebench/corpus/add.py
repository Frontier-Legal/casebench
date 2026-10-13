"""Write a corpus block into casebench.yaml, and describe a live response for the user."""

import re
import textwrap
from collections.abc import Collection
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from casebench.corpus.suggest import _leaves

# Script files whose extension says nothing about the server they start.
SCRIPTS = (".py", ".js", ".mjs", ".ts")


class ConfigHasCorpus(ValueError):
    """The corpus cannot be added as it is: its name is taken, or the file is not in a form
    Casebench edits. Nothing is replaced."""


def describe(response: Any) -> list[str]:
    """One line per field of the first item: its path, type and, for text, its length."""
    lines = []
    for path, value in _leaves(response):
        if isinstance(value, str):
            lines.append(f"{path}  text, {len(value)} characters")
        else:
            lines.append(f"{path}  {value!r}")
    return lines


def corpus_block(
    connector: str, options: dict[str, Any], jurisdictions: list[str] | None = None
) -> dict:
    block: dict[str, Any] = {"connector": connector}
    if jurisdictions:
        block["jurisdictions"] = list(jurisdictions)
    block["options"] = options
    return block


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def name_for(block: dict[str, Any], taken: Collection[str] = ()) -> str:
    """A corpus's default name: its profile's, else its store's host or command, else its
    connector's; `-2`, `-3` and so on when that name is taken."""
    options = block.get("options", {})
    url = options.get("base_url") or options.get("url")
    command = options.get("command") or []
    if block.get("profile"):
        base = Path(str(block["profile"])).stem
    elif isinstance(url, str) and urlsplit(url).hostname:
        base = str(urlsplit(url).hostname).removeprefix("www.")
    elif command:
        program = Path(str(command[-1] if len(command) > 1 else command[0])).name
        base = Path(program).stem if Path(program).suffix in SCRIPTS else program
    else:
        base = str(block.get("connector", "corpus"))
    name = _slug(base) or "corpus"
    number = 1
    while (candidate := name if number == 1 else f"{name}-{number}") in taken:
        number += 1
    return candidate


def taken_names(config: Path) -> set[str]:
    if not config.is_file():
        return set()
    existing = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    return set(existing.get("corpora") or {}) | ({"corpus"} if "corpus" in existing else set())


def _entry(name: str, block: dict[str, Any]) -> str:
    return textwrap.indent(yaml.safe_dump({name: block}, sort_keys=False, allow_unicode=True), "  ")


def write_corpus(config: Path, name: str, block: dict[str, Any]) -> str:
    """Add one named corpus to the config, or create it. An existing corpus is never replaced,
    and a file is only changed by inserting the new entry under `corpora:`."""
    text = "corpora:\n" + _entry(name, block)
    if not config.is_file():
        config.write_text(text, encoding="utf-8")
        return text
    written = config.read_text(encoding="utf-8")
    existing = yaml.safe_load(written) or {}
    if "corpus" in existing:
        both = {"corpora": {"corpus": existing["corpus"], name: block}}
        raise ConfigHasCorpus(
            f"{config} names one corpus under `corpus:`; to add another, put both under "
            f"`corpora:`, each with a name:\n{yaml.safe_dump(both, sort_keys=False)}"
        )
    corpora = existing.get("corpora") or {}
    if name in corpora:
        raise ConfigHasCorpus(f"{config} already has a corpus named {name}; pass --name")
    if "corpora" not in existing:
        with config.open("a", encoding="utf-8") as stream:
            stream.write(("\n" if written.strip() else "") + text)
        return text
    lines = written.splitlines(keepends=True)
    heading = next((i for i, line in enumerate(lines) if line.rstrip() == "corpora:"), None)
    if heading is not None:
        inserted = (
            "".join(lines[: heading + 1]) + _entry(name, block) + "".join(lines[heading + 1 :])
        )
        if (yaml.safe_load(inserted) or {}).get("corpora") == {**corpora, name: block}:
            config.write_text(inserted, encoding="utf-8")
            return _entry(name, block)
    raise ConfigHasCorpus(
        f"{config} lists its corpora in a form Casebench does not edit; add this entry under "
        f"`corpora:` yourself:\n{_entry(name, block)}"
    )
