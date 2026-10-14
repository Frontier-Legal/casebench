"""Init finds the agent's providers and model calls in the code, offline, however many there
are (decision 0040)."""

import json
import os
import socket
from collections.abc import Iterator, MutableMapping
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.capture.backend import backend_step
from casebench.capture.config import CaptureConfig, routes_for
from casebench.capture.step import HttpExchange, StepKind
from casebench.cli import main
from casebench.corpus.binding import CorpusConfig
from casebench.setup.routes import offers
from casebench.setup.scan import scan

AGENT = """\
import os

import httpx
from openai import OpenAI

fireworks = OpenAI(
    base_url=os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"),
    api_key=os.environ["FIREWORKS_API_KEY"],
)
verifier = OpenAI()
documents = httpx.Client(base_url=os.getenv("DOCS_URL", "https://data.example.com/v1"))


def search(question):
    return documents.get("/search", params={"q": question}).json()


def draft(question, found):
    return fireworks.chat.completions.create(
        model="accounts/fireworks/models/kimi-k3", messages=[{"role": "user", "content": question}]
    )


def verify(text):
    return verifier.chat.completions.create(
        model="gpt-5.5", messages=[{"role": "user", "content": text}]
    )


def answer(question):
    return verify(draft(question, search(question)))
"""
# Two catalog entries of one family: the agent's model and a judge that would favour it.
CATALOG = {
    "fireworks": {
        "name": "Fireworks",
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.fireworks.ai/inference/v1",
        "env": ["FIREWORKS_API_KEY"],
        "models": {"accounts/fireworks/models/kimi-k3": {"name": "Kimi K3", "family": "kimi"}},
    },
    "moonshot": {
        "name": "Moonshot",
        "npm": "@ai-sdk/openai-compatible",
        "api": "https://api.moonshot.ai/v1",
        "env": ["MOONSHOT_API_KEY"],
        "models": {"kimi-judge": {"name": "Kimi Judge", "family": "kimi"}},
    },
}
QUIET = ["--corpus", "none", "--no-judge", "--no-extract", "--no-live", "--yes"]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "agent.py").write_text(AGENT, encoding="utf-8")
    # A virtual environment's code is not the project's.
    vendored = tmp_path / ".venv" / "lib" / "anthropic_client.py"
    vendored.parent.mkdir(parents=True)
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    vendored.write_text("import anthropic\nanthropic.Anthropic()\n", encoding="utf-8")
    return tmp_path


def init(*flags: str, typed: str = ""):
    return CliRunner().invoke(main, ["init", *flags], input=typed)


def test_two_providers_found(project: Path):
    command = ["--target", "command", "--run", "python agent.py {question}"]
    made = init(*command, "--routes", "--details", *QUIET)

    assert made.exit_code == 0, made.output
    assert "clients  openai.OpenAI in 2 places" in made.output
    assert (
        "openai.OpenAI at agent.py:6, base URL from FIREWORKS_BASE_URL, else "
        "https://api.fireworks.ai/inference/v1, key from FIREWORKS_API_KEY"
    ) in made.output
    assert "openai.OpenAI at agent.py:10, base URL its SDK's default" in made.output
    assert "anthropic" not in made.output  # the virtual environment was skipped
    assert "✓ openai.OpenAI at agent.py:6: route api-fireworks-ai" in made.output
    assert (
        "openai.OpenAI at agent.py:10: its parser's route, through OPENAI_BASE_URL"
    ) in made.output
    config = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    assert config["capture"]["routes"] == [
        {
            "name": "api-fireworks-ai",
            "upstream": "https://api.fireworks.ai",
            "env": "FIREWORKS_BASE_URL",
            "env_suffix": "/inference/v1",
            "parser": "openai",
        }
    ]


def test_the_agent_s_entry_point_suggested(project: Path):
    made = init("--target", "python", "--no-routes", *QUIET, typed="\n")

    assert made.exit_code == 0, made.output
    # draft and verify reach a model too, but need arguments a case does not give.
    assert "agent.py:answer, the one function Casebench can call" in made.output
    assert "1. agent.py:answer" in made.output
    assert "agent.py:draft" not in made.output
    config = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    assert config["target"]["entry"] == "agent.py:answer"


def test_the_target_s_model_family_known(project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "set")
    catalog = project / "catalog.json"
    catalog.write_text(json.dumps(CATALOG), encoding="utf-8")
    flags = ["--target", "python", "--entry", "agent.py:answer", "--no-routes"]
    flags += ["--corpus", "none", "--no-extract", "--no-live", "--catalog", str(catalog), "--yes"]

    made = init(*flags, "--judge-provider", "moonshot", "--judge-model", "kimi-judge")

    assert made.exit_code == 0, made.output
    assert (
        "warning: the judge is of the kimi family, like accounts/fireworks/models/kimi-k3 in "
        "your agent's code"
    ) in made.stderr


class Watched(MutableMapping[str, str]):
    """The environment, with every name looked up kept, so a test can see none was read."""

    def __init__(self, real: MutableMapping[str, str]) -> None:
        self.real, self.read = real, set()

    def __getitem__(self, key: str) -> str:
        self.read.add(key)
        return self.real[key]

    def __setitem__(self, key: str, value: str) -> None:
        self.real[key] = value

    def __delitem__(self, key: str) -> None:
        del self.real[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.real)

    def __len__(self) -> int:
        return len(self.real)


def test_nothing_leaves_the_machine(project: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-secret-value")
    watched = Watched(os.environ)

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("the scan opened a connection")

    with monkeypatch.context() as patched:
        patched.setattr(os, "environ", watched)
        patched.setattr(socket.socket, "connect", refuse)
        patched.setattr(socket, "create_connection", refuse)
        found = scan(project)
    made = init("--target", "python", "--entry", "agent.py:answer", "--routes", *QUIET)

    assert {client.api_key.env for client in found.clients if client.api_key} == {
        "FIREWORKS_API_KEY"
    }
    assert "FIREWORKS_API_KEY" not in watched.read
    assert "FIREWORKS_BASE_URL" not in watched.read
    assert found.said() == (
        "read 1 Python files as text: names and literals only, no variable's value, and "
        "nothing was sent"
    )
    assert made.exit_code == 0, made.output
    assert found.said() in made.output
    assert "fw-secret-value" not in made.output
    assert "fw-secret-value" not in (project / "casebench.yaml").read_text(encoding="utf-8")


def test_routes_split_by_path(project: Path):
    corpus = CorpusConfig(
        connector="http",
        options={
            "base_url": "https://data.example.com/v1",
            "search_path": "/search",
            "fetch_path": "/documents/{id}",
            "search_results": "$.results[*]",
            "result_fields": {"id": "$.work.work_id"},
        },
    )

    [route] = [
        o.route
        for o in offers(scan(project).clients, {"docs": corpus})
        if o.route and "step" in o.route
    ]
    [written] = [r for r in routes_for(CaptureConfig(routes=[route])) if r.name == route["name"]]
    searched = backend_step(
        HttpExchange(
            method="GET",
            url="https://data.example.com/v1/search?q=fesih",
            status=200,
            response_body={"results": [{"work": {"work_id": "101"}}, {"work": {"work_id": "102"}}]},
        ),
        written,
    )
    read = backend_step(
        HttpExchange(
            method="GET",
            url="https://data.example.com/v1/documents/101",
            status=200,
            response_body={"work_id": "101", "text": "..."},
        ),
        written,
    )

    assert route == {
        "name": "data-example-com",
        "upstream": "https://data.example.com",
        "env": "DOCS_URL",
        "env_suffix": "/v1",
        "step": "retrieval",
        "doc_ids": "$.results[*].work.work_id",
        "fetch_path": "/documents/{id}",
    }
    assert (searched.kind, searched.doc_ids_out) == (StepKind.RETRIEVAL, ["101", "102"])
    assert (read.kind, read.doc_ids_out) == (StepKind.DOCUMENT, ["101"])
