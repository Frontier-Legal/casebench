"""Anyone adds a jurisdiction, a data provider, a model provider or a capture parser as a
plugin."""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import httpx2
import pytest
from click.testing import CliRunner

from casebench.capture.proxy.routes import Route
from casebench.capture.routing import parsers_for_host
from casebench.capture.session import CaptureSession
from casebench.capture.step import Step, StepKind
from casebench.cli import main
from casebench.corpus.binding import Corpus, CorpusConfig
from casebench.plugins import registry
from casebench.plugins.kinds import KINDS, kind_named
from casebench.providers.call import complete
from casebench.providers.interface import HttpRequest, Message
from tests.plugins.entry_points import install
from tests.plugins.fixture_files import (
    NATIONAL_PARSER,
    NATIONAL_SAMPLES,
    venv_python,
    write_decisions,
)
from tests.plugins.national_api import start_national_api

ROOT = Path(__file__).resolve().parents[2]


def test_every_plugin_kind_has_a_contract():
    result = CliRunner().invoke(main, ["plugin", "kinds"])

    assert result.exit_code == 0, result.output
    assert {kind.name for kind in KINDS} == {
        "connector",
        "parser",
        "provider",
        "task",
        "reference",
        "target",
        "metric",
        "exporter",
    }
    for kind in KINDS:
        assert kind.name in result.output
        assert kind.group in result.output
        assert kind.interface_path in result.output
        assert getattr(kind.interface, "_is_protocol", False), kind.interface_path
    assert result.output.count("casebench plugin test <path>") == len(KINDS)


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv to build a test environment")
def test_scaffold_a_plugin(tmp_path: Path):
    runner = CliRunner()
    made = runner.invoke(
        main, ["plugin", "new", "connector", "--name", "acme", "--root", str(tmp_path)]
    )
    assert made.exit_code == 0, made.output
    package = tmp_path / "casebench-acme"
    for path in (
        "casebench_acme/__init__.py",
        "casebench-plugin.json",
        "README.md",
        "tests/test_conformance.py",
        "samples/README.md",
        "pyproject.toml",
    ):
        assert (package / path).is_file(), path

    venv = tmp_path / "venv"
    subprocess.run(
        ["uv", "venv", str(venv), "--python", sys.executable], check=True, capture_output=True
    )
    python = venv_python(venv)
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), "-e", str(ROOT), "-e", str(package)],
        check=True,
        capture_output=True,
    )
    found = subprocess.run(
        [
            str(python),
            "-c",
            "from importlib.metadata import entry_points;"
            "print([p.value for p in entry_points(group='casebench.corpus') if p.name == 'acme'])",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert found.stdout.strip() == "['casebench_acme:Connector']"

    core = tmp_path / "core"
    core.mkdir()
    shutil.copy(ROOT / "pyproject.toml", core / "pyproject.toml")
    built_in = runner.invoke(
        main, ["plugin", "new", "connector", "--name", "acme", "--built-in", "--root", str(core)]
    )
    assert built_in.exit_code == 0, built_in.output
    folder = core / "casebench" / "corpus" / "connectors" / "acme"
    assert (folder / "__init__.py").is_file() and (folder / "casebench-plugin.json").is_file()
    registered = tomllib.loads((core / "pyproject.toml").read_text(encoding="utf-8"))
    connectors = registered["project"]["entry-points"]["casebench.corpus"]
    assert connectors["acme"] == "casebench.corpus.connectors.acme:Connector"


def test_conformance_before_listing(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(main, ["plugin", "new", "parser", "--name", "national", "--root", str(tmp_path)])
    package = tmp_path / "casebench-national"
    (package / "casebench_national" / "__init__.py").write_text(NATIONAL_PARSER, encoding="utf-8")
    for name, sample in NATIONAL_SAMPLES.items():
        (package / "samples" / name).write_text(json.dumps(sample), encoding="utf-8")

    tested = runner.invoke(main, ["plugin", "test", str(package)])
    assert tested.exit_code == 0, tested.output
    assert "parser national: passed, calls parsed 0.50 over 2 samples" in tested.output

    connector = runner.invoke(
        main, ["plugin", "test", str(ROOT / "casebench" / "corpus" / "connectors" / "folder")]
    )
    assert "connector folder: passed, fields covered 1.00 over 2 samples" in connector.output

    stub = tmp_path / "stub"
    runner.invoke(main, ["plugin", "new", "parser", "--name", "acme", "--root", str(stub)])
    failed = runner.invoke(main, ["plugin", "test", str(stub / "casebench-acme")])
    assert failed.exit_code == 1
    assert "parser acme: failed" in failed.output and "holds no samples" in failed.output


def test_a_model_provider_opentelemetry_does_not_know(monkeypatch: pytest.MonkeyPatch):
    install(
        monkeypatch,
        {
            "casebench.capture": {"national": "tests.plugins.fixtures:NationalApiParser"},
            "casebench.providers": {"national": "tests.plugins.fixtures:NationalApiProvider"},
        },
    )
    assert len(parsers_for_host("llm.national.example")) == 1

    api = start_national_api()
    routes = [
        Route(
            name="national",
            upstream=f"http://127.0.0.1:{api.server_port}",
            parser="national",
            env="NATIONAL_BASE_URL",
        )
    ]
    session = CaptureSession(routes)

    async def call_through_the_proxy() -> list[Step]:
        await session.start()
        try:
            session.recorder.begin("c1")
            async with httpx2.AsyncClient() as client:
                await client.post(
                    os.environ["NATIONAL_BASE_URL"] + "/v1/generate",
                    json={"model": "national-large", "turns": []},
                )
            return [step for e in session.recorder.end("c1") for step in session.parse(e)]
        finally:
            await session.stop()

    try:
        [step] = asyncio.run(call_through_the_proxy())
    finally:
        api.shutdown()
    assert (step.kind, step.model, step.input_tokens, step.output_tokens) == (
        StepKind.LLM,
        "national-large",
        812,
        96,
    )

    sent: list[HttpRequest] = []

    def send(request: HttpRequest) -> tuple[int, Any]:
        sent.append(request)
        return 200, {"output": "The termination is invalid.", "usage": {"in": 40, "out": 6}}

    monkeypatch.setenv("NATIONAL_API_KEY", "test-key")
    provider = registry.load(kind_named("provider"), "national")()
    completion = complete(
        provider, [Message(role="user", content="Is it valid?")], "national-large", send
    )
    assert completion.text == "The termination is invalid."
    assert sent[0].url.startswith("https://llm.national.example/")


def test_one_connector_serves_several_countries(tmp_path: Path):
    write_decisions(tmp_path)

    turkish = Corpus(
        CorpusConfig(connector="folder", jurisdiction="tr", options={"path": str(tmp_path)})
    )
    dutch = Corpus(
        CorpusConfig(connector="folder", jurisdiction="nl", options={"path": str(tmp_path)})
    )
    everything = Corpus(CorpusConfig(connector="folder", options={"path": str(tmp_path)}))

    assert turkish.decision_ids() == ["tr-1"]
    assert dutch.decision_ids() == ["nl-1"]
    assert sorted(everything.decision_ids()) == ["nl-1", "tr-1"]
    assert type(turkish.connector) is type(dutch.connector)


def test_framework_code_imports_no_plugin_by_name():
    from tests.plugins.boundary import plugin_leaks

    assert plugin_leaks(ROOT) == []
