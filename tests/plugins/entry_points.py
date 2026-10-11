"""Install plugins for one test without building a distribution."""

from importlib.metadata import EntryPoint

import pytest

from casebench.plugins import registry


def install(monkeypatch: pytest.MonkeyPatch, groups: dict[str, dict[str, str]]) -> None:
    """Replace each named group's entry points with these name-to-object pairs."""
    real = registry.entry_points
    fake = {
        group: [EntryPoint(name, value, group) for name, value in plugins.items()]
        for group, plugins in groups.items()
    }

    def patched(*, group: str) -> list[EntryPoint]:
        return fake[group] if group in fake else list(real(group=group))

    monkeypatch.setattr(registry, "entry_points", patched)
