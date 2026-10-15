"""Onboarding by the user's coding agent from one pasted prompt, with nothing changed in their
code (decision 0044)."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench import keys
from casebench.capture.config import routes_for
from casebench.capture.session import CaptureSession, session_for
from casebench.capture.step import StepKind
from casebench.cli import main
from casebench.config import load_config
from casebench.runs.log import RunInfo, RunLog
from casebench.runs.runner import run_cases
from casebench.targets.load import target_from_config
from tests.capture.openai_upstream import start_openai
from tests.capture.test_proxy_capture import case
from tests.corpus.document_api import KEY, DocumentApi, start_document_api
from tests.judge.fake_judge import start_fake_judge

CATALOG = Path(__file__).parent / "catalog.json"
JUDGE_KEY = "sk-ant-judge-0123456789abcdef"
SETTINGS = '''\
"""The project's own settings loader: production runs it before the agent answers."""

import os
from pathlib import Path


def load() -> None:
    for line in (Path(__file__).parent.parent / "env" / "app.env").read_text().splitlines():
        name, _, value = line.partition("=")
        os.environ.setdefault(name, value)
'''
AGENT = '''\
"""The agent: it reads its own setting, as production starts it."""

import os


def answer_question(question: str) -> str:
    return f"{os.environ['AGENT_SETTING']}: the dismissal is invalid"
'''
ADAPTER = '''\
"""Casebench's adapter: start the agent as production does, then ask it."""

from app.settings import load

load()

from app.agent import answer_question  # noqa: E402


def answer(question: str, facts: str | None = None) -> str:
    return answer_question(question)
'''
DOCUMENT_FIELDS = [
    "--field", "id=$.work_id",
    "--field", "jurisdiction=$.jurisdiction.code",
    "--field", "court=$.issuers[0].name",
    "--field", "date=$.dates[1].date",
    "--field", "text=$.expressions[0].text",
]  # fmt: skip
PATHS = ["--search-path", "/search", "--fetch-path", "/documents/{id}"]
RESULT_FIELDS = [
    "--results", "$.results[*]",
    "--result-field", "id=$.work.work_id",
    "--result-field", "citation=$.citation",
]  # fmt: skip


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(project: Path, *args: str) -> str:
    identity = ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.autocrlf=false"]
    done = subprocess.run(
        ["git", *identity, *args], cwd=project, capture_output=True, text=True, check=True
    )
    return done.stdout


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project as a coding agent finds it: committed, with its keys in env/*.env files."""
    root = tmp_path / "project"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    monkeypatch.setattr(keys, "_held", {})
    for name in ("ANTHROPIC_API_KEY", "DOC_KEY", "AGENT_SETTING", "OPENROUTER_API_KEY"):
        os.environ.pop(name, None)
    write(root / "app" / "__init__.py", "")
    write(root / "app" / "settings.py", SETTINGS)
    write(root / "app" / "agent.py", AGENT)
    write(root / "pyproject.toml", '[project]\nname = "app"\nversion = "1"\n')
    write(root / ".gitignore", "env/*.env\n__pycache__/\n")
    write(root / "env" / "app.env", "AGENT_SETTING=production\n")
    write(root / "env" / "eval.env", f"ANTHROPIC_API_KEY={JUDGE_KEY}\nDOC_KEY={KEY}\n")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "the agent")
    monkeypatch.chdir(root)
    return root


def test_one_prompt_sets_a_project_up(project: Path):
    api, judge = start_document_api(), start_fake_judge()
    base = f"http://127.0.0.1:{api.server_port}/v1"
    corpus = ["--base-url", base, *PATHS, "--key-env", "DOC_KEY"]
    judged = f"base_url=http://127.0.0.1:{judge.server_port}"
    try:
        # What a coding agent does, following `casebench guide` step by step.
        guide = invoke("guide")
        write(project / ".casebench" / "target.py", ADAPTER)
        write(project / ".casebench" / ".gitignore", "*\n!.gitignore\n!target.py\n")
        located = invoke("keys", "ANTHROPIC_API_KEY", "DOC_KEY", "--json")
        listed = invoke("models", "anthropic", "--catalog", str(CATALOG), "--json")
        initialised = invoke(
            "init", "--entry", ".casebench/target.py:answer", "--corpus", "none",
            "--judge-provider", "anthropic", "--judge-model", "judge-model",
            "--judge-option", judged, "--catalog", str(CATALOG),
            "--no-extract", "--no-routes", "--no-live", "--yes",
        )  # fmt: skip
        searched = invoke("corpus", "probe", "http", *corpus, "--query", "feshi", "--fetch", "101")
        added = invoke(
            "corpus", "add", "http", *corpus, "--probe", "feshi",
            *RESULT_FIELDS, *DOCUMENT_FIELDS, "--jurisdiction", "TR", "--yes",
        )  # fmt: skip
        checked = invoke("check", "--json")
    finally:
        api.shutdown()
        judge.shutdown()
    changed = git(project, "status", "--porcelain", "--untracked-files=all").splitlines()

    for step in (guide, located, listed, initialised, searched, added):
        assert step.exit_code == 0, step.output
    assert "judge-model" in [model["id"] for model in json.loads(listed.output)]
    assert "Create only `casebench.yaml` and files under `.casebench/`" in guide.output
    assert json.loads(checked.output)["passed"] is True, checked.output
    assert sorted(changed) == [
        "?? .casebench/.gitignore",
        "?? .casebench/target.py",
        "?? casebench.yaml",
    ]  # nothing the team ships changed
    written = (project / "casebench.yaml").read_text(encoding="utf-8")
    assert yaml.safe_load(written)["keys"] == {
        "ANTHROPIC_API_KEY": "env/eval.env",
        "DOC_KEY": "env/eval.env",
    }
    for step in (located, initialised, searched, added, checked):
        assert JUDGE_KEY not in step.output and KEY not in step.output
    assert JUDGE_KEY not in written and KEY not in written


class RefusingJudge(BaseHTTPRequestHandler):
    """A provider whose refusal repeats the key it was sent."""

    def do_POST(self) -> None:
        payload = json.dumps({"error": f"invalid x-api-key {self.headers['x-api-key']}"}).encode()
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def test_check_speaks_to_a_coding_agent(project: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), RefusingJudge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    write(project / "broken.py", "def answer(question):\n    raise KeyError('FIREWORKS_API_KEY')\n")
    config = {
        "target": {"type": "python", "entry": "broken.py:answer"},
        "judge": {
            "provider": "anthropic",
            "model": "judge-model",
            "options": {"base_url": f"http://127.0.0.1:{server.server_port}", "max_tokens": 64},
        },
        "keys": {"ANTHROPIC_API_KEY": "env/eval.env"},
    }
    write(project / "casebench.yaml", yaml.safe_dump(config))
    try:
        checked = invoke("check", "--json")
    finally:
        server.shutdown()

    assert checked.exit_code == 1
    report = json.loads(checked.output)
    parts = {part["part"]: part for part in report["parts"]}
    assert report["passed"] is False
    assert parts["target"]["passed"] is False
    assert parts["target"]["reason"].endswith("KeyError: 'FIREWORKS_API_KEY'")
    assert "settings the agent reads loaded first" in parts["target"]["next"]
    assert parts["judge"]["passed"] is False
    assert "${ANTHROPIC_API_KEY}" in parts["judge"]["reason"]  # the key by name
    assert parts["judge"]["next"].startswith("the provider refused the key")
    assert JUDGE_KEY not in checked.output


def test_a_key_is_located_by_name(project: Path):
    write(project / "research" / ".env", "SHARED_KEY=first-value-aaaa\n")
    write(project / "env" / "shared.env", "SHARED_KEY=second-value-bbbb\nOTHER=1\n")

    located = invoke("keys", "SHARED_KEY", "DOC_KEY", "MISSING_KEY", "--json")
    # The files that disagree are settled with --key, which is recorded however init runs:
    # writing a new setup, updating one, or with the variable also set in the shell.
    agent = ["--entry", "app/agent.py:answer_question", "--corpus", "none", "--no-judge"]
    quiet = ["--no-extract", "--no-routes", "--no-live", "--yes"]
    made = invoke("init", *agent, *quiet, "--key", "SHARED_KEY=env/shared.env")
    os.environ["DOC_KEY"] = KEY
    updated = invoke("init", *agent, *quiet, "--key", "DOC_KEY=env/eval.env")
    no_file = invoke("init", *agent, *quiet, "--key", "OTHER=env/none.env")
    recorded = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))["keys"]

    assert located.exit_code == 0, located.output
    assert made.exit_code == 0, made.output
    assert updated.exit_code == 0, updated.output
    assert recorded == {"SHARED_KEY": "env/shared.env", "DOC_KEY": "env/eval.env"}
    assert no_file.exit_code == 2
    assert "env/none.env is not a file under" in no_file.output
    shared, doc, missing = json.loads(located.output)
    assert sorted(item["file"] for item in shared["files"]) == ["env/shared.env", "research/.env"]
    assert shared["values_agree"] is False
    assert len({item["fingerprint"] for item in shared["files"]}) == 2
    assert doc == {
        "name": "DOC_KEY",
        "in_shell": False,
        "files": [{"file": "env/eval.env", "fingerprint": keys.fingerprint(KEY)}],
        "values_agree": True,
    }
    assert missing["files"] == []
    for value in ("first-value", "second-value", KEY, JUDGE_KEY):
        assert value not in located.output


def test_the_corpus_is_described_from_one_probe(project: Path):
    api = start_document_api()
    # The project keeps the store's address in a .env file, as it keeps the key.
    write(project / "env" / "docs.env", f"DOCS_URL=http://127.0.0.1:{api.server_port}/v1\n")
    corpus = ["--base-url", "${DOCS_URL}", *PATHS, "--key-env", "DOC_KEY"]
    try:
        searched = invoke("corpus", "probe", "http", *corpus, "--query", "feshi")
        fetched = invoke("corpus", "probe", "http", *corpus, "--fetch", "101")
        added = invoke(
            "corpus", "add", "http", *corpus, "--probe", "feshi",
            *RESULT_FIELDS, *DOCUMENT_FIELDS, "--yes",
        )  # fmt: skip
    finally:
        api.shutdown()

    assert searched.exit_code == 0, searched.output
    response = json.loads(searched.output)["search"]["response"]
    assert response["results"][0]["work"]["work_id"] == "101"
    assert json.loads(fetched.output)["document"]["response"]["work_id"] == "101"
    assert added.exit_code == 0, added.output
    config = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    [block] = config["corpora"].values()
    assert block["probe"] == "feshi"
    assert block["options"]["result_fields"] == {"id": "$.work.work_id", "citation": "$.citation"}
    assert block["options"]["fields"]["text"] == "$.expressions[0].text"
    assert block["options"]["base_url"] == "${DOCS_URL}"  # named, not held
    assert config["keys"] == {"DOCS_URL": "env/docs.env", "DOC_KEY": "env/eval.env"}
    for step in (searched, fetched, added):
        assert KEY not in step.output


def test_check_reuses_the_setups_search(project: Path):
    os.environ["DOC_KEY"] = KEY
    api = start_document_api()
    DocumentApi.searches = []
    options = {
        "base_url": f"http://127.0.0.1:{api.server_port}/v1",
        "headers": {"Authorization": "Bearer ${DOC_KEY}"},
        "search_path": "/search",
        "search_params": {"q": "{text}"},
        "fetch_path": "/documents/{id}",
        "search_results": "$.results[*]",
        "result_fields": {"id": "$.work.work_id"},
        "fields": {
            "id": "$.work_id",
            "jurisdiction": "$.jurisdiction.code",
            "court": "$.issuers[0].name",
            "date": "$.dates[1].date",
            "text": "$.expressions[0].text",
        },
    }
    corpus = {"connector": "http", "options": options, "probe": "feshi"}
    write(project / "casebench.yaml", yaml.safe_dump({"corpus": corpus}))
    try:
        checked = invoke("check")
    finally:
        api.shutdown()

    assert checked.exit_code == 0, checked.output
    assert checked.output.startswith("corpus   passed")
    assert DocumentApi.searches == ["feshi"]


def test_an_adapter_in_casebench_reaches_the_projects_code(
    project: Path, monkeypatch: pytest.MonkeyPatch
):
    write(project / ".casebench" / "target.py", ADAPTER)
    target = {"type": "python", "entry": ".casebench/target.py:answer"}
    write(project / "casebench.yaml", yaml.safe_dump({"target": target}))
    elsewhere = project.parent / "elsewhere"
    elsewhere.mkdir()

    from_root = invoke("check")
    monkeypatch.chdir(elsewhere)
    from_elsewhere = invoke("check", "--config", str(project / "casebench.yaml"))

    for checked in (from_root, from_elsewhere):
        assert checked.exit_code == 0, checked.output
        assert checked.output.startswith("target   passed")
        assert "no call was recorded" in checked.output  # this adapter calls no model


def test_a_hard_coded_url_is_still_recorded(project: Path):
    upstream = start_openai()
    literal = f"http://127.0.0.1:{upstream.server_port}/v1"
    agent = project / "agent.py"
    write(
        agent,
        "from openai import OpenAI\n\n"
        f'client = OpenAI(base_url="{literal}", api_key="not-a-real-key")\n\n\n'
        "def answer(question):\n"
        "    asked = [{'role': 'user', 'content': question}]\n"
        "    reply = client.chat.completions.create(model='gpt-5', messages=asked)\n"
        "    return reply.choices[0].message.content\n",
    )
    before = hashlib.sha256(agent.read_bytes()).hexdigest()
    init = ["init", "--entry", "agent.py:answer", "--corpus", "none", "--no-judge"]
    initialised = invoke(*init, "--no-extract", "--routes", "--no-live", "--yes")
    config = load_config(project / "casebench.yaml")
    session = CaptureSession(routes_for(config.capture))
    target = target_from_config(config.target or {})
    log = RunLog.create(
        project / "run", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="python")
    )
    try:
        [result] = asyncio.run(
            run_cases([case("c1", "Is it valid?")], target, log, capture=session)
        )
    finally:
        upstream.shutdown()

    assert initialised.exit_code == 0, initialised.output
    assert "each model and search call is recorded where it goes" in initialised.output
    assert result.error is None, result.error
    assert result.output == "Short: invalid."
    [call] = [step for step in result.steps if step.kind is StepKind.LLM]
    assert (call.provider, call.model, call.input_tokens) == ("openai", "gpt-5", 30)
    assert hashlib.sha256(agent.read_bytes()).hexdigest() == before


def test_a_judge_on_openrouter_needs_no_api_question(project: Path):
    catalog = project.parent / "catalog.json"
    entry = {
        "name": "OpenRouter",
        "npm": "@openrouter/ai-sdk-provider",
        "api": "https://openrouter.ai/api/v1",
        "env": ["OPENROUTER_API_KEY"],
        "models": {"google/gemini-x": {"family": "gemini"}},
    }
    catalog.write_text(json.dumps({"openrouter": entry}), encoding="utf-8")
    os.environ["OPENROUTER_API_KEY"] = "or-key"
    judge = ["--judge-provider", "openrouter", "--judge-model", "google/gemini-x"]

    made = invoke(
        "init", "--entry", "app/agent.py:answer_question", "--corpus", "none", *judge,
        "--catalog", str(catalog), "--no-extract", "--no-routes", "--no-live", "--yes",
    )  # fmt: skip

    assert made.exit_code == 0, made.output
    assert "which API does" not in made.output
    written = yaml.safe_load((project / "casebench.yaml").read_text(encoding="utf-8"))
    assert written["judge"]["provider"] == "openai"
    assert written["judge"]["options"]["base_url"] == "https://openrouter.ai/api/v1"
    assert written["judge"]["options"]["api_key_env"] == "OPENROUTER_API_KEY"


ASKS = """
def answer(question):
    asked = [{"role": "user", "content": question}]
    reply = OpenAI().chat.completions.create(model="gpt-5", messages=asked)
    return reply.choices[0].message.content
"""


def test_a_key_reaches_only_the_host_the_agent_chose(
    project: Path, monkeypatch: pytest.MonkeyPatch
):
    upstream = start_openai()
    chosen = f"http://127.0.0.1:{upstream.server_port}/v1"
    # A Python agent's own settings choose its provider, as a settings loader does.
    write(
        project / "python_agent.py",
        "import os\n\nfrom openai import OpenAI\n\n"
        f"os.environ.setdefault('OPENAI_BASE_URL', '{chosen}')\n"
        "os.environ.setdefault('OPENAI_API_KEY', 'a-key-for-that-provider')\n\n" + ASKS,
    )
    write(
        project / "command_agent.py",
        "import sys\n\nfrom openai import OpenAI\n\n" + ASKS + "\n\nprint(answer(sys.argv[1]))\n",
    )
    runs = {
        "python": {"type": "python", "entry": str(project / "python_agent.py")},
        "command": {"type": "command", "run": f"{sys.executable} command_agent.py {{question}}"},
    }
    results = {}
    try:
        for kind, target in runs.items():
            if kind == "command":  # a command agent's provider is set in the shell
                monkeypatch.setenv("OPENAI_BASE_URL", chosen)
                monkeypatch.setenv("OPENAI_API_KEY", "a-key-for-that-provider")
            log = RunLog.create(
                project / kind, RunInfo(run_id=kind, suite_id="s", suite_hash="h", target=kind)
            )
            session = CaptureSession(routes_for(None))
            agent = target_from_config(target)
            [results[kind]] = asyncio.run(
                run_cases([case("c1", "Is it valid?")], agent, log, capture=session)
            )
    finally:
        upstream.shutdown()

    for kind, result in results.items():
        assert result.error is None, (kind, result.error)  # not sent to api.openai.com
        assert result.output == "Short: invalid.", kind
        [call] = [step for step in result.steps if step.kind is StepKind.LLM]
        assert (call.provider, call.model) == ("openai", "gpt-5"), kind


SEARCHES = """
import os

import requests


def answer(question):
    base, key = os.environ["DOCS_URL"], {"Authorization": f"Bearer {os.environ['DOC_KEY']}"}
    hits = requests.get(f"{base}/search", params={"q": question}, headers=key).json()["results"]
    if not hits:
        return "No decision speaks to that."
    found = hits[0]["work"]["work_id"]
    return requests.get(f"{base}/documents/{found}", headers=key).json()["work_id"]
"""


def test_an_agents_own_search_is_recorded(project: Path):
    api = start_document_api()
    os.environ["DOCS_URL"] = f"http://127.0.0.1:{api.server_port}/v1"
    os.environ["DOC_KEY"] = KEY
    write(project / "searching_agent.py", SEARCHES)
    corpus = {
        "connector": "http",
        "options": {
            "base_url": "${DOCS_URL}",
            "headers": {"Authorization": "Bearer ${DOC_KEY}"},
            "search_path": "/search",
            "fetch_path": "/documents/{id}",
            "search_results": "$.results[*]",
            "result_fields": {"id": "$.work.work_id"},
            "fields": {
                "id": "$.work_id",
                "jurisdiction": "$.jurisdiction.code",
                "court": "$.issuers[0].name",
                "date": "$.dates[1].date",
                "text": "$.expressions[0].text",
            },
        },
        "probe": "feshi",
    }
    target = {"type": "python", "entry": "searching_agent.py:answer"}
    write(project / "casebench.yaml", yaml.safe_dump({"target": target, "corpus": corpus}))
    config = load_config(project / "casebench.yaml")
    log = RunLog.create(
        project / "run", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="python")
    )
    session = session_for(config.capture, config.corpora)
    try:
        [result] = asyncio.run(
            run_cases(
                [case("c1", "feshi")], target_from_config(config.target or {}), log, capture=session
            )
        )
        # check greets the agent, which searches for the greeting and finds nothing.
        checked = invoke("check")
    finally:
        api.shutdown()

    assert checked.exit_code == 0, checked.output
    assert (
        'target   passed: answered "No decision speaks to that.", 1 call recorded (1 retrieval)'
        in checked.output
    )
    assert result.error is None, result.error
    assert result.output == "101"
    [searched] = [step for step in result.steps if step.kind is StepKind.RETRIEVAL]
    [read] = [step for step in result.steps if step.kind is StepKind.DOCUMENT]
    assert searched.doc_ids_out == ["101"]
    assert read.doc_ids_out == ["101"]
