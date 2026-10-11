"""Write a corpus block into casebench.yaml, and describe a live response for the user."""

from pathlib import Path
from typing import Any

import yaml

from casebench.corpus.suggest import _leaves


class ConfigHasCorpus(ValueError):
    """The config already names a corpus; Casebench never rewrites it."""


def describe(response: Any) -> list[str]:
    """One line per field of the first item: its path, type and, for text, its length."""
    lines = []
    for path, value in _leaves(response):
        if isinstance(value, str):
            lines.append(f"{path}  text, {len(value)} characters")
        else:
            lines.append(f"{path}  {value!r}")
    return lines


def corpus_block(connector: str, options: dict[str, Any], jurisdiction: str | None) -> dict:
    block: dict[str, Any] = {"connector": connector}
    if jurisdiction:
        block["jurisdiction"] = jurisdiction
    block["options"] = options
    return block


def write_corpus(config: Path, block: dict[str, Any]) -> str:
    """Append the block to the config, or create it; refuse to replace an existing corpus."""
    text = yaml.safe_dump({"corpus": block}, sort_keys=False, allow_unicode=True)
    if config.is_file():
        existing = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        if "corpus" in existing:
            raise ConfigHasCorpus(
                f"{config} already names a corpus; replace it with this block yourself:\n{text}"
            )
        with config.open("a", encoding="utf-8") as stream:
            stream.write(("\n" if config.read_text(encoding="utf-8").strip() else "") + text)
    else:
        config.write_text(text, encoding="utf-8")
    return text
