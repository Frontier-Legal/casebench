"""Script paths in casebench.yaml are relative to the file."""

from pathlib import Path

from casebench.config import relative_to


def test_a_relative_script_is_read_from_the_configs_folder(tmp_path: Path):
    assert relative_to(tmp_path, "agents/agent.py:answer") == (
        f"{(tmp_path / 'agents' / 'agent.py').resolve()}:answer"
    )
    assert relative_to(tmp_path, "agent.py") == str((tmp_path / "agent.py").resolve())


def test_modules_and_absolute_paths_are_left_alone(tmp_path: Path):
    absolute = str((tmp_path / "agent.py").resolve())
    assert relative_to(tmp_path, "firm.agent:answer") == "firm.agent:answer"
    assert relative_to(tmp_path, f"{absolute}:answer") == f"{absolute}:answer"
