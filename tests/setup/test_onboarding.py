"""Onboarding a real project in a few Enter presses: detect first, keys from .env files, a guided
terminal UI (decision 0043)."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import load_config
from casebench.setup import judge_question, models
from tests.corpus.document_api import KEY, start_document_api

CATALOG = Path(__file__).parent / "catalog.json"
SECRET = "sk-ant-secret-0123456789abcdef"
AGENT = """\
from openai import OpenAI

client = OpenAI()


def answer(question):
    return client.chat.completions.create(model="real-model", messages=[]).choices[0]


def _helper(question):
    return client.chat.completions.create(model="real-model", messages=[])
"""
JUDGE = ["--judge-provider", "anthropic", "--judge-model", "judge-model", "--catalog", str(CATALOG)]


def init(*flags: str, typed: str = ""):
    return CliRunner().invoke(main, ["init", *flags], input=typed)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    # Init sets a key it found in this process's environment; each test gets its own.
    monkeypatch.setattr(os, "environ", os.environ.copy())
    for name in ("ANTHROPIC_API_KEY", "DOC_KEY", "MY_JUDGE_KEY"):
        os.environ.pop(name, None)
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    return tmp_path


def env_file(path: Path, lines: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k}={v}\n" for k, v in lines.items()), encoding="utf-8")


def test_a_key_in_a_env_file_is_found(project: Path):
    env_file(project / ".env", {"DATABASE_URL": "postgres://local"})
    env_file(project / "web" / ".env.local", {"OTHER": "1"})
    env_file(project / "env" / "eval.env", {"OTHER": "1", "ANTHROPIC_API_KEY": SECRET})
    env_file(project / "env" / "eval.env.example", {"ANTHROPIC_API_KEY": "your-key-here"})
    flags = ["--entry", "agent.py:answer", "--corpus", "none", "--no-extract", "--no-live"]

    made = init(*flags, *JUDGE, "--no-routes", "--yes")
    os.environ.pop("ANTHROPIC_API_KEY")  # a later command starts without it
    config = load_config(project / "casebench.yaml")  # as every later command reads it
    read_later = os.environ.get("ANTHROPIC_API_KEY")

    assert made.exit_code == 0, made.output
    assert "✓ key ANTHROPIC_API_KEY in env/eval.env" in made.output
    assert "which .env file" not in made.output  # found, so not asked
    written = (project / "casebench.yaml").read_text(encoding="utf-8")
    assert SECRET not in made.output
    assert SECRET not in written
    assert config.keys == {"ANTHROPIC_API_KEY": "env/eval.env"}
    assert read_later == SECRET


def test_two_env_files_disagree_or_none_has_the_name(project: Path):
    env_file(project / "research" / ".env", {"ANTHROPIC_API_KEY": "sk-ant-aaaa-first-111111"})
    env_file(project / "services" / ".env", {"ANTHROPIC_API_KEY": "sk-ant-bbbb-second-22222"})
    flags = ["--entry", "agent.py:answer", "--corpus", "none", "--no-extract", "--no-live"]

    disagree = init(*flags, *JUDGE, "--no-routes", "--yes", typed="2\n")
    chosen = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))

    for path in (project / "research", project / "services"):
        (path / ".env").unlink()
    os.environ.pop("ANTHROPIC_API_KEY")  # set by the first init, as for the rest of its run
    (project / "casebench.yaml").unlink()
    env_file(project / ".env", {"MY_JUDGE_KEY": "sk-ant-mine-33333333", "DB_URL": "x"})
    # The only .env file (1), then the first name in it (1).
    named = init(*flags, *JUDGE, "--no-routes", "--yes", typed="1\n1\n")
    renamed = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))

    assert disagree.exit_code == 0, disagree.output
    assert "ANTHROPIC_API_KEY has different values in these files" in disagree.output
    assert "research/.env  (sk-a…1111)" in disagree.output  # masked, enough to tell apart
    assert "sk-ant-aaaa-first-111111" not in disagree.output
    assert chosen["keys"] == {"ANTHROPIC_API_KEY": "services/.env"}
    assert named.exit_code == 0, named.output
    assert "judge: which key in .env?" in named.output
    assert "1. MY_JUDGE_KEY" in named.output  # names only
    assert "sk-ant-mine" not in named.output
    assert renamed["judge"]["options"]["api_key_env"] == "MY_JUDGE_KEY"
    assert renamed["keys"] == {"MY_JUDGE_KEY": ".env"}


def test_quick_start_asks_only_what_is_missing(project: Path):
    env_file(project / ".env", {"ANTHROPIC_API_KEY": SECRET, "DOC_KEY": KEY})
    api = start_document_api()
    base = f"http://127.0.0.1:{api.server_port}/v1"
    # The corpus: its address, the two suggested paths, its key's file (1) and name (2), a
    # search; then which response field is which, as nothing is guessed from names.
    corpus = f"{base}\n\n\n1\n2\nfeshi\n"
    fields = "\n$.work.work_id\n$.citation\n$.document_type\n$.highlight\n"
    fields += "\n$.jurisdiction.code\n$.issuers[0].name\n\n\n\n"
    try:
        made = init(
            "--quick", "--corpus", "http", *JUDGE, "--no-live", "--yes", typed=corpus + fields
        )
    finally:
        api.shutdown()

    assert made.exit_code == 0, made.output
    for asked in (
        "How does Casebench reach your agent?",  # a function was found
        "Which function answers a question?",  # it is the only one Casebench can call
        "judge: which .env file",  # its key is in the one .env file that has it
        "Make test cases from many court decisions",  # not in Quick start
        "Record openai.OpenAI",  # a route is taken, not asked
    ):
        assert asked not in made.output
    assert "✓ agent agent.py:answer, the one function Casebench can call" in made.output
    config = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    assert config["target"] == {"type": "python", "entry": "agent.py:answer"}
    assert config["keys"] == {"DOC_KEY": ".env", "ANTHROPIC_API_KEY": ".env"}
    [corpus_block] = config["corpora"].values()
    assert corpus_block["options"]["result_fields"]["citation"] == "$.citation"


def test_a_short_summary_on_a_large_project(project: Path):
    service = project / "service"
    service.mkdir()
    (service / "agent.py").write_text(
        AGENT
        + "\nimport httpx\n\n"
        + "plain = [httpx.Client() for _ in range(3)]\n"
        + 'search = httpx.Client(base_url="https://search.example/v1")\n\n\n'
        + "def run(question, extra):\n    return answer(question)\n",
        encoding="utf-8",
    )
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_agent.py").write_text(
        "from openai import OpenAI\n\nOpenAI().chat.completions.create(model='test-only-model')\n",
        encoding="utf-8",
    )
    flags = ["--entry", "agent.py:answer", "--corpus", "none", "--no-judge", "--no-extract"]

    short = init(*flags, "--no-live", "--no-routes", "--yes")
    (project / "casebench.yaml").unlink()
    detailed = init(*flags, "--no-live", "--no-routes", "--yes", "--details")

    assert short.exit_code == 0, short.output
    assert "2 functions Casebench can call; you pick one" in short.output
    assert "clients  openai.OpenAI in 2 places · httpx.Client in 1 place" in short.output
    assert "models   real-model" in short.output
    for left_out in ("test-only-model", "_helper", "service/agent.py:run", "tests/test_agent.py"):
        assert left_out not in short.output
    assert "entry agent.py:answer" not in short.output  # the detail stays behind --details
    assert detailed.exit_code == 0, detailed.output
    assert "entry agent.py:answer" in detailed.output
    assert "entry service/agent.py:answer" in detailed.output
    assert "httpx.Client at service/agent.py:16, base URL https://search.example/v1" in (
        detailed.output
    )


class Provider(BaseHTTPRequestHandler):
    """An OpenAI-compatible provider that refuses the key for one model and answers another."""

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body["model"] == "refused-model":
            status, reply = 401, {"error": {"message": "invalid api key"}}
        else:
            message = {"role": "assistant", "content": '{"ok": true}'}
            status, reply = 200, {"choices": [{"message": message}], "usage": {}}
        payload = json.dumps(reply).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def test_a_failed_check_loops_back(project: Path, monkeypatch: pytest.MonkeyPatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    catalog = project / "catalog.json"
    models_listed = {"refused-model": {"family": "acme"}, "working-model": {"family": "acme"}}
    catalog.write_text(
        json.dumps(
            {
                "acme": {
                    "name": "Acme",
                    "npm": "@ai-sdk/openai-compatible",
                    "api": f"http://127.0.0.1:{server.server_port}/v1",
                    "env": ["ACME_KEY"],
                    "models": models_listed,
                }
            }
        ),
        encoding="utf-8",
    )
    os.environ["ACME_KEY"] = "a-key"
    picked = iter(["acme", "refused-model", "acme", "working-model"])
    monkeypatch.setattr(models, "pick", lambda *_, **__: next(picked))
    asked: list[str] = []
    monkeypatch.setattr(judge_question, "interactive", lambda: True)
    monkeypatch.setattr(judge_question, "pick", lambda q, *_: asked.append(q) or "other")
    flags = ["--entry", "agent.py:answer", "--corpus", "none", "--no-extract", "--no-routes"]
    try:
        made = init(*flags, "--catalog", str(catalog), "--yes")
    finally:
        server.shutdown()

    assert made.exit_code == 0, made.output
    assert "✗ the judge did not answer: the provider refused the key" in made.output
    assert asked == ["The judge did not answer. What now?"]
    assert "✓ openai working-model answered" in made.output
    config = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    assert config["judge"]["model"] == "working-model"  # no restart, the second pick kept


def test_reviewed_before_writing(project: Path):
    flags = ["--entry", "agent.py:answer", "--corpus", "none", "--no-judge", "--no-extract"]

    declined = init(*flags, "--no-live", "--no-routes", typed="n\n")

    assert declined.exit_code == 0, declined.output
    assert "casebench.yaml will hold" in declined.output
    assert "target  agent.py:answer" in declined.output
    assert "Nothing was written." in declined.output
    assert not (project / "casebench.yaml").exists()
