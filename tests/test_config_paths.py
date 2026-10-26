"""Script paths and folder corpus paths in casebench.yaml are relative to the file."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import load_config, relative_to


def test_a_relative_script_is_read_from_the_configs_folder(tmp_path: Path):
    assert relative_to(tmp_path, "agents/agent.py:answer") == (
        f"{(tmp_path / 'agents' / 'agent.py').resolve()}:answer"
    )
    assert relative_to(tmp_path, "agent.py") == str((tmp_path / "agent.py").resolve())


def test_modules_and_absolute_paths_are_left_alone(tmp_path: Path):
    absolute = str((tmp_path / "agent.py").resolve())
    assert relative_to(tmp_path, "firm.agent:answer") == "firm.agent:answer"
    assert relative_to(tmp_path, f"{absolute}:answer") == f"{absolute}:answer"


def test_a_folder_corpus_is_read_from_the_configs_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    project, elsewhere = tmp_path / "project", tmp_path / "elsewhere"
    (project / "decisions").mkdir(parents=True)
    elsewhere.mkdir()
    record = {
        "id": "2024-1",
        "jurisdiction": "TR",
        "court": "Yargıtay",
        "date": "2024-03-01",
        "text": "The appeal is upheld.",
    }
    (project / "decisions" / "2024-1.json").write_text(json.dumps(record), encoding="utf-8")
    absolute = (tmp_path / "shared").resolve().as_posix()
    config = project / "casebench.yaml"
    config.write_text(
        "corpora:\n"
        "  near: {connector: folder, options: {path: decisions}}\n"
        f"  far: {{connector: folder, options: {{path: '{absolute}'}}}}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(elsewhere)

    checked = CliRunner().invoke(
        main, ["corpus", "check", "--config", str(config), "--corpus", "near"]
    )

    assert checked.exit_code == 0, checked.output
    assert "sampled 1 documents" in checked.output
    corpora = load_config(config).corpora
    assert corpora["near"].options["path"] == str((project / "decisions").resolve())
    assert corpora["far"].options["path"] == absolute
