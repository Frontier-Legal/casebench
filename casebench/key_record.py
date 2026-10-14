"""Record in casebench.yaml which file each key is read from: its name and the file, no value."""

from pathlib import Path

import yaml


class KeysNotRecorded(ValueError):
    """The config's `keys` is written in a form lines cannot be added to."""


def _lines(keys: dict[str, str]) -> str:
    return "".join(f"  {name}: {file}\n" for name, file in keys.items())


def record_keys(config: Path, keys: dict[str, str]) -> dict[str, str]:
    """Add each name the config's `keys` lacks, by inserting lines, so comments and the rest
    stay as they are (decision 0043). A name already there keeps its file. Returns what was
    added."""
    written = config.read_text(encoding="utf-8") if config.is_file() else ""
    existing = (yaml.safe_load(written) or {}).get("keys") or {}
    added = {name: file for name, file in keys.items() if name not in existing}
    if not added:
        return {}
    lines = written.splitlines(keepends=True)
    heading = next((i for i, line in enumerate(lines) if line.rstrip() == "keys:"), None)
    if heading is None and "keys" in (yaml.safe_load(written) or {}):
        raise KeysNotRecorded(f"add these under `keys:` in {config}:\n{_lines(added)}")
    if heading is None:
        text = written + ("\n" if written and not written.endswith("\n") else "")
        text += "keys:\n" + _lines(added)
    else:
        text = "".join(lines[: heading + 1]) + _lines(added) + "".join(lines[heading + 1 :])
    if (yaml.safe_load(text) or {}).get("keys") != {**existing, **added}:
        raise KeysNotRecorded(f"add these under `keys:` in {config}:\n{_lines(added)}")
    config.write_text(text, encoding="utf-8")
    return added
