"""Nothing leaves the perimeter: a run calls only the hosts its config names, follows no
redirect to another host, writes no key, and treats output as data (decision 0046)."""

import json
import os
import socket
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import CliRunner

from casebench import keys
from casebench.cli import main
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.runs.log import RunLog
from casebench.suites.freeze import freeze
from tests.corpus.document_api import KEY, DocumentApi, start_document_api
from tests.judge.fake_judge import FakeJudge, start_fake_judge
from tests.perimeter.servers import serve, url
from tests.setup.test_setup_spends_little import corpus

AGENT_KEY = "agent-model-key-0123456789"
JUDGE_KEY = "judge-model-key-9876543210"
CITING = "The dismissal is invalid: Yargıtay 9. HD, E. 2023/1234 K. 2024/567."


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(keys, "_held", {})
    os.environ["DOC_KEY"] = KEY
    os.environ["ANTHROPIC_API_KEY"] = JUDGE_KEY
    os.environ["AGENT_KEY"] = AGENT_KEY
    DocumentApi.searches, DocumentApi.fetches = [], {}
    return tmp_path


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def suite(project: Path, cases: int = 1, metrics: list[str] | None = None) -> str:
    asked = [
        Case(
            id=f"c{n}",
            task=Task.model_validate({"type": "qa", "question": f"Is dismissal {n} valid?"}),
            reference=Reference(source=ReferenceSource.LAWYER),
            metrics=metrics or [],
        )
        for n in range(1, cases + 1)
    ]
    freeze("perimeter", asked, project / "suite")
    return "suite"


def judge(port: int) -> dict[str, Any]:
    options = {"base_url": f"http://127.0.0.1:{port}", "max_tokens": 256}
    return {"provider": "anthropic", "model": "judge-model", "options": options}


def configure(project: Path, **config: Any) -> None:
    (project / "casebench.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")


def python_agent(project: Path, body: str) -> dict[str, str]:
    (project / "agent.py").write_text(body, encoding="utf-8")
    return {"type": "python", "entry": "agent.py:answer"}


def written(folder: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in folder.rglob("*") if path.is_file()
    )


def test_allowlist_enforced(project: Path):
    target = python_agent(
        project,
        "import httpx2\n\n"
        "def answer(question):\n"
        "    httpx2.get('http://elsewhere.example/collect')\n"
        "    return 'answered'\n",
    )
    judged = start_fake_judge()
    configure(
        project, target=target, judge=judge(judged.server_port), network={"allow": ["ok.example"]}
    )
    try:
        ran = invoke("run", "--suite", suite(project), "--run-id", "r")
    finally:
        judged.shutdown()

    assert ran.exit_code != 0
    assert "refused a call to elsewhere.example" in ran.output
    assert "network: allow:" in ran.output
    # The case is not stored, so a resumed run sends it again once the host is allowed.
    assert RunLog(project / ".casebench" / "runs" / "r").results() == []


def test_no_telemetry(project: Path, monkeypatch: pytest.MonkeyPatch):
    agent = serve(lambda *_: (200, {}, {"answer": CITING}))
    judged, documents = start_fake_judge(), start_document_api()
    configure(
        project,
        target={
            "type": "http",
            "url": url(agent, "/ask"),
            "body": {"q": "{{question}}"},
            "answer": "$.answer",
        },
        judge=judge(judged.server_port),
        corpus=corpus(documents.server_port),
    )
    named = suite(project, metrics=["citation_integrity"])
    connected: list[tuple[str, int]] = []
    looked_up: list[str] = []
    connect, getaddrinfo = socket.socket.connect, socket.getaddrinfo

    def recorded_connect(self: socket.socket, address: Any) -> None:
        connected.append((address[0], address[1]))
        return connect(self, address)

    def recorded_lookup(host: Any, *rest: Any, **options: Any) -> Any:
        looked_up.append(str(host))
        return getaddrinfo(host, *rest, **options)

    monkeypatch.setattr(socket.socket, "connect", recorded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", recorded_lookup)
    try:
        ran = invoke("run", "--suite", named, "--run-id", "r")
    finally:
        monkeypatch.undo()
        for server in (agent, judged, documents):
            server.shutdown()

    assert ran.exit_code == 0, ran.output
    # The run called the target, the judge and the corpus, and nothing else.
    assert FakeJudge.calls and DocumentApi.searches
    called = {port for _, port in connected}
    assert called == {agent.server_port, judged.server_port, documents.server_port}
    assert {host for host, _ in connected} <= {"127.0.0.1"}
    assert set(looked_up) <= {"127.0.0.1", "localhost"}


def test_keys_never_land_on_disk(project: Path):
    model = serve(lambda *_: (200, {}, {"ok": True}))
    target = python_agent(
        project,
        "import os\n\nimport httpx2\n\n"
        "def answer(question):\n"
        "    key = os.environ['AGENT_KEY']\n"
        f"    called = {url(model, '/v1/chat')!r}\n"
        "    httpx2.post(called, headers={'Authorization': f'Bearer {key}'})\n"
        "    if '2' in question:\n"
        "        raise RuntimeError(f'the model refused {key}')\n"
        "    return f\"{key} and {os.environ['ANTHROPIC_API_KEY']}. \" + "
        f"{CITING!r}\n",
    )
    judged, documents = start_fake_judge(), start_document_api()
    configure(
        project,
        target=target,
        judge=judge(judged.server_port),
        corpus=corpus(documents.server_port),
    )
    try:
        ran = invoke("run", "--suite", suite(project, 2, ["citation_integrity"]), "--run-id", "r")
    finally:
        for server in (model, judged, documents):
            server.shutdown()

    assert ran.exit_code == 0, ran.output
    run = written(project / ".casebench" / "runs" / "r")
    config = (project / "casebench.yaml").read_text(encoding="utf-8")
    for value in (AGENT_KEY, JUDGE_KEY, KEY):
        assert value not in run and value not in config and value not in ran.output
    # The key the agent sent in its Authorization header, and the judge's key by its name.
    assert "[credential] and ${ANTHROPIC_API_KEY}." in run
    assert "the model refused [credential]" in run
    assert "${DOC_KEY}" in config


def test_output_is_data_never_code(project: Path):
    output = (
        "<script>alert(1)</script> {{7*7}} ${HOME} $(touch pwned) "
        "[bold red]loud[/bold red] __import__('os').system('touch pwned') " + CITING
    )
    target = python_agent(project, f"def answer(question):\n    return {output!r}\n")
    judged, documents = start_fake_judge(), start_document_api()
    configure(
        project,
        target=target,
        judge=judge(judged.server_port),
        corpus=corpus(documents.server_port),
    )
    try:
        ran = invoke(
            "run", "--suite", suite(project, metrics=["citation_integrity"]), "--run-id", "r"
        )
        shown = invoke("target", "check", "--question", "Is it valid?")
    finally:
        judged.shutdown()
        documents.shutdown()

    assert ran.exit_code == 0, ran.output
    [result] = RunLog(project / ".casebench" / "runs" / "r").results()
    assert result.output == output
    assert shown.exit_code == 0, shown.output
    assert f"answer     {output}" in shown.output
    assert not list(project.glob("pwned*"))
    report = json.loads((project / ".casebench" / "runs" / "r" / "report.json").read_text())
    assert report["scores"]


def test_redirects_do_not_escape(project: Path):
    away = {"Location": "http://elsewhere.example/collect"}
    moved = serve(lambda *_: (302, away, {}))
    (project / "http").mkdir()
    (project / "python").mkdir()
    configure(
        project / "http",
        target={
            "type": "http",
            "url": url(moved, "/ask"),
            "body": {"q": "{{question}}"},
            "answer": "$.answer",
        },
    )
    target = python_agent(
        project / "python",
        "import httpx2\n\n"
        "def answer(question):\n"
        f"    return httpx2.get({url(moved, '/ask')!r}, follow_redirects=True).text\n",
    )
    configure(project / "python", target=target)
    suite(project)
    try:
        ran = {
            kind: invoke(
                "run",
                "--suite",
                str(project / "suite"),
                "--config",
                str(project / kind / "casebench.yaml"),
                "--runs-dir",
                str(project / kind / "runs"),
            )
            for kind in ("http", "python")
        }
    finally:
        moved.shutdown()

    for kind in ("http", "python"):
        assert ran[kind].exit_code != 0, ran[kind].output
        assert "refused a redirect from 127.0.0.1 to elsewhere.example" in ran[kind].output
