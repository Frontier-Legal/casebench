"""Say what reading the project found: one line per kind, and every finding on request."""

import os
from collections import Counter
from pathlib import Path

from casebench import envfiles
from casebench.setup.scan import Scan, Source
from casebench.setup.sdks import detect


def _where_key(name: str, root: Path, files: list[Path]) -> str:
    if os.environ.get(name):
        return f"{name}, set in this shell"
    holder = next((p for p in files if envfiles.value(p, name)), None)
    if holder is None:
        return f"{name}, not found"
    return f"{name} in {holder.relative_to(root).as_posix()}"


def sdks(root: Path) -> tuple[str, str]:
    """The SDKs the project's dependency files name that a capture parser reads (0040)."""
    found = detect(root)
    if not found:
        return ("SDKs", "none a parser reads; the proxy still records the routes it knows")
    return (
        "SDKs",
        " · ".join(f"{package}, read by the {parser} parser" for package, parser in found.items()),
    )


def summary(found: Scan, root: Path, entry: str | None = None) -> list[tuple[str, str]]:
    """The functions Casebench could call as the agent, or the one given, the model clients
    and names, and where their keys are. Nothing is suggested from names: a function is
    listed because a case's inputs fit its signature and it reaches a model call (0043)."""
    rows = [sdks(root)]
    if entry is not None:
        rows.append(("agent", f"{entry}, as given; {len(found.entries)} could be called"))
    elif len(found.entries) == 1:
        rows.append(("agent", f"{found.entries[0]}, the one function Casebench can call"))
    elif found.entries:
        rows.append(("agent", f"{len(found.entries)} functions Casebench can call; you pick one"))
    else:
        rows.append(("agent", "no function Casebench can call with a question; you name it"))
    clients = Counter(client.kind for client in found.clients)
    if clients:
        said = (f"{kind} in {n} place{'s' if n > 1 else ''}" for kind, n in clients.items())
        rows.append(("clients", " · ".join(said)))
    names = sorted({model.name for model in found.models})
    if names:
        rows.append(("models", ", ".join(names)))
    keyed = sorted({c.api_key.env for c in found.clients if c.api_key and c.api_key.env})
    if keyed:
        files = envfiles.env_files(root)
        rows.append(("keys", " · ".join(_where_key(name, root, files) for name in keyed)))
    rows.append(("scanned", found.said()))
    return rows


def _source(source: Source | None) -> str:
    if source is None:
        return "its SDK's default"
    if source.env and source.literal:
        return f"from {source.env}, else {source.literal}"
    return f"from {source.env}" if source.env else source.literal or "unknown"


def details(found: Scan) -> list[str]:
    """Every client with where its base URL and key come from, every model and every entry."""
    lines = []
    for client in found.clients:
        key = f", key {_source(client.api_key)}" if client.api_key else ""
        lines.append(f"{client.kind} at {client.where}, base URL {_source(client.base_url)}{key}")
    first: dict[str, str] = {}
    for model in found.models:
        first.setdefault(model.name, f"{model.path}:{model.line}")
    lines += [f"model {name} at {where}" for name, where in first.items()]
    lines += [f"entry {entry}" for entry in found.entries]
    return lines
