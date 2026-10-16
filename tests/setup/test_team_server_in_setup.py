"""Init asks whether lawyers review on a team server, names it, or shows how to set one up;
push says where a server comes from (decision 0064). The check against a running server is in
ee/team_tests/test_team_server_check.py."""

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.setup import team_question

SERVER = "https://casebench.firm.example"
KEY_VALUE = "cbk_not-a-real-key-but-shaped-like-one"
FLAGS = [
    "--entry",
    "agent.py:answer",
    "--corpus",
    "none",
    "--no-judge",
    "--no-extract",
    "--no-routes",
    "--no-live",
    "--yes",
]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CASEBENCH_CLOUD_KEY", KEY_VALUE)
    (tmp_path / "agent.py").write_text(
        "def answer(question: str) -> str:\n    return 'The appeal is upheld.'\n", "utf-8"
    )
    return tmp_path


def init(*args: str):
    return CliRunner().invoke(main, ["init", *args])


def written(project: Path) -> dict:
    return yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))


def test_a_team_server_we_have(project: Path):
    made = init(*FLAGS, "--team-server", f"{SERVER}/")
    moved = init("--team-server", "https://review.firm.example", "--no-routes", "--yes")

    assert made.exit_code == 0, made.output
    assert "team server" in made.output and f"{SERVER} · key CASEBENCH_CLOUD_KEY" in made.output
    assert "Set CASEBENCH_CLOUD_KEY here" in made.output
    assert "casebench push" in made.output and "casebench invite EMAIL" in made.output
    # The address is named; the key is the user's to set, and never written or shown.
    assert moved.exit_code == 0, moved.output
    assert "team server https://review.firm.example, instead of " + SERVER in moved.output
    assert written(project)["cloud"] == {"url": "https://review.firm.example"}
    for output in (made.output, moved.output, (project / "casebench.yaml").read_text("utf-8")):
        assert KEY_VALUE not in output


def test_setting_one_up(project: Path, monkeypatch: pytest.MonkeyPatch):
    asked: list[str] = []
    monkeypatch.setattr(team_question, "interactive", lambda: True)
    monkeypatch.setattr(
        team_question, "pick", lambda q, choices, *_, **__: asked.append(q) or team_question.SET_UP
    )

    made = init(*FLAGS)

    assert made.exit_code == 0, made.output
    assert asked == ["Will lawyers review on a team server?"]
    # What to run on the server lawyers reach; nothing is installed or written here.
    assert "pip install casebench-ee" in made.output
    assert "casebench-team serve" in made.output
    assert "one-time setup code" in made.output
    assert "API key with the engineer role" in made.output
    assert f"casebench init --team-server {SERVER}" in made.output
    assert "cloud" not in written(project)


def test_not_now(project: Path, monkeypatch: pytest.MonkeyPatch):
    # Without a terminal and without --team-server, nothing is asked.
    scripted = init(*FLAGS)
    (project / "casebench.yaml").unlink()
    monkeypatch.setattr(team_question, "interactive", lambda: True)
    monkeypatch.setattr(team_question, "pick", lambda q, choices, default, **__: default)
    chosen = init(*FLAGS)

    for made in (scripted, chosen):
        assert made.exit_code == 0, made.output
        assert "Lawyers review on this machine: casebench ui" in made.output
        assert "casebench init --team-server URL" in made.output
    assert "cloud" not in written(project)


def test_push_says_where_a_server_comes_from(project: Path):
    (project / "casebench.yaml").write_text("{}\n", encoding="utf-8")

    pushed = CliRunner().invoke(main, ["push"])

    assert pushed.exit_code != 0
    assert "names no team server" in pushed.output
    assert "casebench init --team-server URL" in pushed.output
    assert "casebench-ee, installed on a machine lawyers reach" in pushed.output
    assert "ee/README.md" in pushed.output
