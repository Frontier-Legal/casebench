"""Init names the SDK and the search store a project uses, asks only for the corpus and the
judge, and writes a config an editor can check (decision 0061)."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

import pytest
import yaml
from click.testing import CliRunner

from casebench import keys
from casebench.capture.searches import search_step
from casebench.capture.step import HttpExchange, StepKind
from casebench.cli import main
from casebench.setup.config_schema import LINE, SCHEMA_FILE
from tests.judge.fake_judge import start_fake_judge

CATALOG = Path(__file__).parent / "catalog.json"
PYPROJECT = """\
[project]
name = "legal-agent"
version = "0.1.0"
dependencies = ["anthropic>=1.13", "qdrant-client>=1.12"]
"""
# The agent searches its Qdrant collection through httpx, as the Qdrant client's REST calls do,
# then asks its model; a greeting needs no model.
AGENT = """\
import os

import anthropic
import httpx

client = anthropic.Anthropic()


def answer(question):
    found = httpx.post(
        os.environ["QDRANT_URL"] + "/collections/decisions/points/search",
        json={"vector": [0.1, 0.2], "limit": 2},
    ).json()["result"]
    if question.startswith("Hi"):
        return "Hello. I answer questions about employment law."
    return client.messages.create(model="claude-sonnet-5-5", max_tokens=200, messages=[]).content
"""


class Qdrant(BaseHTTPRequestHandler):
    searched: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers["Content-Length"]))
        Qdrant.searched.append(self.path)
        points = [{"id": "dec-1", "score": 0.9}, {"id": "dec-2", "score": 0.8}]
        payload = json.dumps({"result": points, "status": "ok", "time": 0.001}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(keys, "_held", {})
    os.environ["ANTHROPIC_API_KEY"] = "a-judge-key"
    (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    decisions = tmp_path / "decisions"
    decisions.mkdir()
    (decisions / "dec-1.json").write_text(
        json.dumps({"id": "dec-1", "court": "Court of Appeal", "text": "Dismissal is void."}),
        encoding="utf-8",
    )
    return tmp_path


def test_init_detects_the_stack(project: Path):
    qdrant = ThreadingHTTPServer(("127.0.0.1", 0), Qdrant)
    threading.Thread(target=qdrant.serve_forever, daemon=True).start()
    judge = start_fake_judge()
    os.environ["QDRANT_URL"] = f"http://127.0.0.1:{qdrant.server_port}"
    Qdrant.searched = []
    # Only the corpus and the judge are given: any other question would stop init, which
    # has no terminal here.
    asked = [
        "--quick", "--entry", "agent.py:answer",
        "--corpus", "folder", "--corpus-path", "decisions",
        "--judge-provider", "anthropic", "--judge-model", "judge-model", "--catalog", str(CATALOG),
        "--judge-option", f"base_url=http://127.0.0.1:{judge.server_port}",
        "--no-extract", "--yes",
    ]  # fmt: skip
    try:
        made = CliRunner().invoke(main, ["init", *asked])
    finally:
        qdrant.shutdown()
        judge.shutdown()
    written = (project / "casebench.yaml").read_text(encoding="utf-8")
    schema = json.loads((project / SCHEMA_FILE).read_text(encoding="utf-8"))

    assert made.exit_code == 0, made.output
    # The SDK and the search store, from the dependency file.
    assert "anthropic, read by the anthropic parser" in made.output
    assert "Qdrant (qdrant-client), its searches recorded as retrievals" in made.output
    # The config names its schema, which knows every key the config holds.
    assert written.startswith(LINE)
    assert set(yaml.safe_load(written)) <= set(schema["properties"])
    assert "Casebench points your agent at its recorder itself" in made.output
    # One sample: the greeting, its parsed answer, and the store's search recorded.
    assert Qdrant.searched == ["/collections/decisions/points/search"]
    assert (
        'target: answered "Hello. I answer questions about employment law.", '
        "1 call recorded (1 retrieval)"
    ) in made.output


def test_an_agent_already_running_gets_its_environment_lines(project: Path):
    (project / "agent.py").write_text(
        "import os\n\nimport anthropic\n\n"
        'client = anthropic.Anthropic(base_url=os.environ.get("MODEL_URL", '
        '"https://models.example.com/v1"))\n\n\n'
        "def answer(question):\n"
        '    return client.messages.create(model="m", max_tokens=9, messages=[])\n',
        encoding="utf-8",
    )
    flags = ["--quick", "--url", "http://127.0.0.1:8000/ask", "--routes"]
    quiet = ["--corpus", "none", "--no-judge", "--no-extract", "--no-live", "--yes"]

    made = CliRunner().invoke(main, ["init", *flags, *quiet], input='{"q": "{question}"}\n$.a\n')

    assert made.exit_code == 0, made.output
    assert "MODEL_URL=http://127.0.0.1:7463/models-example-com/v1" in made.output


def test_a_qdrant_search_is_a_retrieval():
    searched = HttpExchange(
        method="POST",
        url="https://qdrant.example.com/collections/law/points/query",
        status=200,
        response_body={"result": {"points": [{"id": 7}, {"id": "dec-9"}]}},
    )
    other = searched.model_copy(update={"url": "https://qdrant.example.com/collections/law"})

    step = search_step(searched)

    assert step is not None
    assert (step.kind, step.name, step.doc_ids_out) == (
        StepKind.RETRIEVAL,
        "Qdrant search",
        ["7", "dec-9"],
    )
    assert search_step(other) is None
