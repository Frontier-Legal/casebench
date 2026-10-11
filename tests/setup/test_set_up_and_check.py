"""Set up in the agent's checkout; check and run where the agent and the corpus are reachable."""

import json
import socket
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.capture.step import StepKind
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import RunLog
from casebench.setup.sdks import detect
from casebench.suites.freeze import freeze
from tests.capture.upstreams import start_upstream
from tests.corpus.document_api import KEY, start_document_api
from tests.judge.fake_judge import start_fake_judge

PLAIN_AGENT = Path(__file__).resolve().parents[1] / "capture" / "plain_http_agent.py"
CATALOG = Path(__file__).resolve().parent / "catalog.json"


def closed_port() -> int:
    """A port nothing listens on: what a production host looks like from a laptop."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-judge-key")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "agent"\nversion = "0"\n'
        'dependencies = ["anthropic>=0.40", "litellm", "requests"]\n',
        encoding="utf-8",
    )
    (tmp_path / "agent.py").write_text(
        "def answer(question: str) -> str:\n    return 'The appeal is upheld.'\n",
        encoding="utf-8",
    )
    return tmp_path


def test_set_up_in_the_checkout(checkout: Path):
    production = f"http://127.0.0.1:{closed_port()}"

    ran = CliRunner().invoke(
        main,
        [
            "init",
            "--target",
            "python",
            "--entry",
            "agent.py:answer",
            "--corpus",
            "http",
            "--judge-provider",
            "anthropic",
            "--judge-model",
            "judge-model",
            "--judge-option",
            f"base_url={production}",
            "--no-extract",
            "--catalog",
            str(CATALOG),
        ],
        input=f"{production}\n/search\n/documents/{{id}}\n\ndismissal\n",
    )

    assert ran.exit_code == 0, ran.output
    assert "found    anthropic: read by the anthropic parser" in ran.output
    assert "litellm" not in ran.output  # no installed parser reads it
    assert "corpus   not reachable from here; run `casebench corpus add http`" in ran.output
    assert "target   passed" in ran.output
    assert "judge    not reachable from here" in ran.output
    assert "run `casebench check` where the rest is reachable" in ran.output
    written = (checkout / "casebench.yaml").read_text(encoding="utf-8")
    assert "secret-judge-key" not in written
    config = yaml.safe_load(written)
    assert config["target"] == {"type": "python", "entry": "agent.py:answer"}
    assert config["judge"]["options"]["max_tokens"] == 256  # the model's output limit


def test_init_refuses_an_entry_that_does_not_exist(checkout: Path):
    ran = CliRunner().invoke(
        main,
        [
            "init",
            "--target",
            "python",
            "--entry",
            "agent.py:missing",
            "--corpus",
            "none",
            "--no-judge",
            "--no-extract",
            "--no-live",
        ],
    )

    assert ran.exit_code != 0
    assert "agent.py defines no 'missing'" in ran.output
    assert not (checkout / "casebench.yaml").exists()


def test_checked_and_run_where_it_is_reachable(checkout: Path):
    upstream = start_upstream()
    judge = start_fake_judge()
    base = f"http://127.0.0.1:{upstream.server_port}"
    corpus = checkout / "decisions"
    corpus.mkdir()
    record = {"id": "tr-1", "jurisdiction": "TR", "court": "Yargıtay", "date": "2024-01-01"}
    (corpus / "tr-1.json").write_text(json.dumps({**record, "text": "Karar."}), encoding="utf-8")
    config = {
        "target": {"type": "command", "run": f"{sys.executable} {PLAIN_AGENT} {{question}}"},
        "corpus": {"connector": "folder", "options": {"path": str(corpus)}},
        "judge": {
            "provider": "anthropic",
            "model": "judge-model",
            "options": {"base_url": f"http://127.0.0.1:{judge.server_port}", "max_tokens": 256},
        },
        "capture": {
            "routes": [
                {"name": "anthropic", "upstream": base},
                {
                    "name": "search",
                    "upstream": base,
                    "env": "SEARCH_URL",
                    "doc_ids": "$.result[*].id",
                },
            ]
        },
    }
    (checkout / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    case = Case(
        id="c1",
        task=Task.model_validate({"type": "qa", "question": "Is the dismissal valid?"}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=[],
    )
    freeze("server", [case], checkout / "suite")
    try:
        checked = CliRunner().invoke(main, ["check"])
        ran = CliRunner().invoke(main, ["run", "--suite", "suite", "--run-id", "r"])
    finally:
        upstream.shutdown()
        judge.shutdown()

    assert checked.exit_code == 0, checked.output
    assert "corpus   passed: 1 documents sampled" in checked.output
    assert "target   passed" in checked.output
    assert "judge    passed" in checked.output
    assert ran.exit_code == 0, ran.output
    [result] = RunLog(checkout / ".casebench" / "runs" / "r").results()
    kinds = [step.kind for step in result.steps]
    assert StepKind.LLM in kinds and StepKind.TOOL in kinds
    [search] = [s for s in result.steps if s.kind is StepKind.RETRIEVAL]
    assert search.doc_ids_out == ["tr-1", "tr-2"]


def test_check_fails_when_a_part_is_out_of_reach(checkout: Path):
    production = f"http://127.0.0.1:{closed_port()}"
    (checkout / "casebench.yaml").write_text(
        yaml.safe_dump(
            {
                "target": {"type": "python", "entry": "agent.py:answer"},
                "judge": {
                    "provider": "anthropic",
                    "model": "judge-model",
                    "options": {"base_url": production, "max_tokens": 256},
                },
            }
        ),
        encoding="utf-8",
    )

    checked = CliRunner().invoke(main, ["check"])

    assert checked.exit_code == 1
    assert "target   passed" in checked.output
    assert "judge    not reachable from here" in checked.output


def test_sdks_found_in_a_lock_and_a_package_json(tmp_path: Path):
    (tmp_path / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "OpenAI"\nversion = "1"\n'
        '[[package]]\nname = "google_genai"\nversion = "1"\n',
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"@anthropic-ai/sdk": "^1"}, "devDependencies": {}}),
        encoding="utf-8",
    )

    assert detect(tmp_path) == {
        "@anthropic-ai/sdk": "anthropic",
        "google-genai": "gemini",
        "openai": "openai",
    }


def test_a_corpus_that_refuses_says_why(checkout: Path, monkeypatch: pytest.MonkeyPatch):
    api = start_document_api()
    base = f"http://127.0.0.1:{api.server_port}/v1"
    asked = f"{base}\n/search\n/documents/{{id}}\nDOC_KEY\nfeshi\n"
    flags = ["init", "--target", "python", "--entry", "agent.py:answer", "--corpus", "http"]
    flags += ["--no-judge", "--no-extract", "--no-live"]
    monkeypatch.setenv("DOC_KEY", "a-wrong-key")
    try:
        refused = CliRunner().invoke(main, flags, input=asked)
        (checkout / "casebench.yaml").unlink()
        monkeypatch.setenv("DOC_KEY", KEY)
        added = CliRunner().invoke(main, flags, input=asked + "\n" * 8)
    finally:
        api.shutdown()

    assert refused.exit_code == 0, refused.output
    assert (
        "corpus   not added: the API answered 401 to the search: it needs an API key, or the "
        "key it got is wrong"
    ) in refused.output
    assert added.exit_code == 0, added.output
    assert "corpus   added after one live search and fetch" in added.output
    corpus = yaml.safe_load((checkout / "casebench.yaml").read_text("utf-8"))["corpus"]
    assert corpus["options"]["headers"] == {"Authorization": "Bearer ${DOC_KEY}"}
