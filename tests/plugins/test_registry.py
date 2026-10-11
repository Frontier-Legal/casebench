"""The registry, the boundary check and the scaffold's pyproject edit, in detail."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.plugins.scaffold import check_name, register_entry_point
from tests.plugins.boundary import plugin_leaks


def test_two_sources_for_one_name_must_be_chosen_between(monkeypatch: pytest.MonkeyPatch):
    def point(source: str) -> SimpleNamespace:
        # An installed entry point as the registry sees it: a name and its distribution.
        return SimpleNamespace(
            name="national",
            value="tests.plugins.fixtures:NationalApiParser",
            dist=SimpleNamespace(name=source),
        )

    clash = [point("casebench"), point("casebench-national")]
    monkeypatch.setattr(registry, "entry_points", lambda *, group: clash)
    parsers = kind_named("parser")

    with pytest.raises(registry.PluginClash, match="Add `source: <distribution>`"):
        registry.find(parsers, "national")
    assert registry.find(parsers, "national", source="casebench-national").name == "national"
    with pytest.raises(registry.PluginNotFound, match="no parser named 'regional'"):
        registry.find(parsers, "regional")


def test_the_boundary_check_finds_an_import_and_a_name(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project.entry-points."casebench.capture"]\nzz = "casebench.capture.parsers.zz:Parser"\n',
        encoding="utf-8",
    )
    plugin = tmp_path / "casebench" / "capture" / "parsers" / "zz"
    plugin.mkdir(parents=True)
    (plugin / "__init__.py").write_text('CODE = "zz"\n', encoding="utf-8")
    core = tmp_path / "casebench" / "core"
    core.mkdir()
    (core / "leak.py").write_text(
        '"""Mentions zz only in a docstring."""\n'
        "from casebench.capture.parsers.zz import CODE\n"
        'DEFAULT = "zz"\n',
        encoding="utf-8",
    )

    assert plugin_leaks(tmp_path) == [
        "casebench.core.leak imports casebench.capture.parsers.zz",
        "casebench.core.leak names the plugin 'zz'",
    ]


def test_registering_adds_to_an_existing_table_and_refuses_a_repeat(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\n\n[project.entry-points."casebench.corpus"]\n'
        'folder = "casebench.corpus.connectors.folder:Connector"\n',
        encoding="utf-8",
    )
    register_entry_point(
        pyproject, "casebench.corpus", "s3", "casebench.corpus.connectors.s3:Connector"
    )
    register_entry_point(
        pyproject, "casebench.capture", "acme", "casebench.capture.parsers.acme:Parser"
    )
    text = pyproject.read_text(encoding="utf-8")
    assert text.count('[project.entry-points."casebench.corpus"]') == 1
    assert 's3 = "casebench.corpus.connectors.s3:Connector"' in text
    assert '[project.entry-points."casebench.capture"]\nacme = ' in text
    with pytest.raises(ValueError, match="already registers 'acme'"):
        register_entry_point(pyproject, "casebench.capture", "acme", "x:y")


@pytest.mark.parametrize("name", ["FR", "fr-be", "1fr", ""])
def test_plugin_names_are_lowercase_identifiers(name: str):
    with pytest.raises(ValueError):
        check_name(name)
