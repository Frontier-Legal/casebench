"""Bundled profiles: listed by name only, checked offline, and offered first by `casebench init`."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

import casebench.corpus
from casebench.cli import main
from casebench.corpus.bundled import SAMPLES, bundled, offline_problems
from casebench.report.render import WAITING
from casebench.setup.corpus_question import LATER, OTHERS, choices
from tests.corpus.document_api import KEY, start_document_api, work
from tests.corpus.profiles import http_options, profile
from tests.report.suites import frozen, mixed

AGENTS = Path(__file__).parents[1] / "report" / "agents.py"


@pytest.fixture
def shelf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty folder standing in for the profiles bundled with Casebench."""
    folder = tmp_path / "bundled"
    folder.mkdir()
    monkeypatch.setattr("casebench.corpus.bundled.PROFILES", folder)
    return folder


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[str]:
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.chdir(tmp_path)
    server = start_document_api()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def shelved(
    shelf: Path, file_name: str, name: str, key_env: str, base: str = "http://x", **extra: Any
) -> None:
    options = http_options(base)
    profile(shelf, "http", options, file_name=file_name, name=name, key_env=key_env, **extra)


def record(shelf: Path, profile_id: str, search: Any, fetch: Any) -> None:
    folder = shelf / SAMPLES / profile_id
    folder.mkdir(parents=True)
    (folder / "search.json").write_text(json.dumps(search), encoding="utf-8")
    (folder / "fetch.json").write_text(json.dumps(fetch, ensure_ascii=False), encoding="utf-8")


def test_every_bundled_profile_passes_its_offline_check():
    for item in bundled():
        assert offline_problems(item) == [], item.id


def test_a_bundled_profile_needs_recorded_responses_that_its_paths_read(shelf: Path):
    shelved(shelf, "acme.yaml", "Acme", "ACME_KEY")
    [item] = bundled()
    expected = shelf / SAMPLES / "acme" / "search.json"
    assert offline_problems(item) == [f"acme has no recorded search: add {expected}"]

    record(shelf, "acme", {"results": [{"work": {"work_id": "101"}}]}, work("101"))
    assert offline_problems(item) == ["acme: a bundled profile names its maintainer"]

    shelved(shelf, "acme.yaml", "Acme", "ACME_KEY", maintainer="Acme <data@acme.example>")
    [item] = bundled()
    assert offline_problems(item) == []

    (shelf / SAMPLES / "acme" / "fetch.json").write_text("{}", encoding="utf-8")
    assert offline_problems(item) == [
        "acme: the recorded fetch gives no id, jurisdiction, court, date, text"
    ]


def test_profiles_are_listed_by_name_and_only_a_found_key_is_preselected(
    shelf: Path, monkeypatch: pytest.MonkeyPatch
):
    shelved(shelf, "zeta.yaml", "Zeta Law", "ZETA_KEY")
    shelved(shelf, "alpha.yaml", "alpha data", "ALPHA_KEY")
    shelved(shelf, "mid.yaml", "Mid Courts", "MID_KEY")
    for name in ("ZETA_KEY", "ALPHA_KEY", "MID_KEY"):
        monkeypatch.delenv(name, raising=False)

    listed, preselected = choices()
    assert [value for _, value in listed] == [
        "profile:alpha",
        "profile:mid",
        "profile:zeta",
        *(value for _, value in OTHERS),
    ]
    assert preselected is None

    monkeypatch.setenv("ZETA_KEY", "k")
    monkeypatch.setenv("MID_KEY", "k")
    listed, preselected = choices()
    assert preselected == "profile:mid"
    assert [title for title, _ in listed][:3] == [
        "alpha data  (TR)",
        "Mid Courts  (TR)  · key found",
        "Zeta Law  (TR)  · key found",
    ]
    docs = (Path(casebench.corpus.__file__).parent / "profiles" / "README.md").read_text("utf-8")
    assert "by name, in alphabetical order" in docs
    assert "None is listed above another" in docs


def test_init_connects_a_bundled_profile_picked_from_the_list(
    api: str, shelf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    shelved(shelf, "test-provider.yaml", "Test Provider", "DOC_KEY", api)
    (tmp_path / "agent.py").write_text("def answer(q: str) -> str:\n    return 'x'\n", "utf-8")
    asked: dict[str, Any] = {}

    answers = iter(["profile:test-provider", "none"])  # the provider, then "that's all"
    second: dict[str, Any] = {}

    def picked(message: str, listed: list, default: str | None = None) -> str:
        (second if asked else asked).update(message=message, listed=listed, default=default)
        return next(answers)

    monkeypatch.setattr("casebench.setup.corpus_question.pick", picked)

    ran = CliRunner().invoke(
        main,
        ["init", "--target", "python", "--entry", "agent.py:answer", "--no-judge", "--no-extract"],
    )

    assert ran.exit_code == 0, ran.output
    assert asked["message"].startswith("Connect a source of court decisions?")
    assert asked["default"] == "profile:test-provider"
    assert second["message"].startswith("Connect another source?")
    assert ("that's all", "none") in second["listed"]
    assert "profile:test-provider" not in [value for _, value in second["listed"]]
    assert "corpus   Test Provider: searched 'feshi' and fetched document 101" in ran.output
    config = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    assert config["corpora"]["test-provider"]["profile"] == "test-provider"

    again = CliRunner().invoke(
        main, ["corpus", "add", "profile", "test-provider", "--config", "other.yaml"]
    )
    assert again.exit_code == 0, again.output


def test_not_now_says_citation_checks_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agent.py").write_text("def answer(q: str) -> str:\n    return 'x'\n", "utf-8")

    ran = CliRunner().invoke(
        main,
        [
            "init",
            "--target",
            "python",
            "--entry",
            "agent.py:answer",
            "--corpus",
            "none",
            "--no-judge",
            "--no-extract",
            "--no-live",
        ],
    )

    typed = "Is the dismissal valid?\nNo.\n4857 sayılı İş Kanunu m. 18\n\nAv. Deniz Kaya\ny\n"
    written = CliRunner().invoke(
        main, ["case", "new", "--manual", "--suite", "lawyer"], input=typed
    )
    suite = frozen(mixed(3), tmp_path / "outcomes")
    scored = CliRunner().invoke(
        main, ["run", "--suite", str(suite), "--python", f"{AGENTS}:upheld", "--no-capture"]
    )

    assert ran.exit_code == 0, ran.output
    assert LATER in ran.output
    assert "corpus" not in yaml.safe_load((tmp_path / "casebench.yaml").read_text("utf-8"))
    assert written.exit_code == 0, written.output  # cases are written by hand
    assert "they resolve with a corpus, then casebench case resolve" in written.output
    assert scored.exit_code == 0, scored.output
    assert WAITING in scored.output  # and the report says what waits for a corpus


def test_enter_takes_the_profile_whose_key_was_found():
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from casebench.setup.picker import pick

    listed = [("Alpha", "profile:alpha"), ("Mid  · key found", "profile:mid"), *OTHERS]
    with create_pipe_input() as typing:
        typing.send_text("\r")
        assert pick("q", listed, "profile:mid", input=typing, output=DummyOutput()) == "profile:mid"
