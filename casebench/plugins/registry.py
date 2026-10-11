"""Find and load plugins by the name a config gives.

This is the only place a plugin is imported.
"""

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from casebench.plugins.kinds import PluginKind


class PluginNotFound(LookupError):
    pass


class PluginClash(LookupError):
    pass


@dataclass(frozen=True)
class Available:
    """One installed plugin, before it is loaded."""

    name: str
    value: str
    source: str | None


def installed(kind: PluginKind) -> list[EntryPoint]:
    """Entry points registered in the kind's group by every installed distribution."""
    return list(entry_points(group=kind.group))


def _source(point: EntryPoint) -> str | None:
    dist = getattr(point, "dist", None)
    return dist.name if dist is not None else None


def available(kind: PluginKind) -> list[Available]:
    return sorted(
        (Available(point.name, point.value, _source(point)) for point in installed(kind)),
        key=lambda item: (item.name, item.source or ""),
    )


def find(kind: PluginKind, name: str, source: str | None = None) -> EntryPoint:
    """The one entry point a config means. Two distributions claiming one name is an
    error unless the config names the source."""
    matches = [point for point in installed(kind) if point.name == name]
    if source is not None:
        matches = [point for point in matches if _source(point) == source]
    if not matches:
        where = f" from {source}" if source else ""
        raise PluginNotFound(f"no {kind.name} named {name!r}{where} is installed")
    if len(matches) > 1:
        sources = sorted(str(_source(point)) for point in matches)
        raise PluginClash(
            f"{len(matches)} installed distributions register a {kind.name} named {name!r}: "
            f"{', '.join(sources)}. Add `source: <distribution>` to the config to choose one."
        )
    return matches[0]


def load(kind: PluginKind, name: str, source: str | None = None) -> Any:
    """Import the plugin's object only now, when a config selects it."""
    return find(kind, name, source).load()
