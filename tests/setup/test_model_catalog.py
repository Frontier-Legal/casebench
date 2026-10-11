"""Models Casebench calls itself, picked from the public catalog and called the project's way."""

import json
import sys
import types
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from casebench.cli import main
from casebench.config import CasebenchConfig
from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.setup import models
from casebench.setup.catalog import offer
from casebench.setup.checks import offline
from casebench.setup.picker import pick

CATALOG = Path(__file__).resolve().parent / "catalog.json"
ENTRIES = json.loads(CATALOG.read_text(encoding="utf-8"))


def scripted(answers: list[str]):
    """Stands in for the menu: each call takes the next answer, which must be on offer."""
    remaining = list(answers)

    def choose(message: str, choices: list[tuple[str, str]], **_: object) -> str:
        answer = remaining.pop(0)
        assert answer in [value for _, value in choices], (message, answer)
        return answer

    return choose


def test_models_picked_from_the_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    monkeypatch.setattr(
        models,
        "pick",
        scripted(
            [
                "fireworks-ai",
                "accounts/fireworks/models/qwen-x",
                "fireworks-ai",
                "accounts/fireworks/models/kimi-x",
                "groq",
                "llama-x",
                "openai",  # no installed provider names Groq's API; the user says which
            ]
        ),
    )
    (tmp_path / "agent.py").write_text("def answer(question):\n    return 'x'\n", "utf-8")

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
            "--catalog",
            str(CATALOG),
            "--no-live",
        ],
        input="y\nhttps://api.groq.com/openai/v1\n",
    )

    assert ran.exit_code == 0, ran.output
    assert "its key is read from FIREWORKS_API_KEY, not set here" in ran.output
    config = yaml.safe_load((tmp_path / "casebench.yaml").read_text("utf-8"))
    assert config["judge"] == {
        "provider": "openai",
        "model": "accounts/fireworks/models/qwen-x",
        "options": {
            "base_url": "https://api.fireworks.ai/inference/v1/",
            "api_key_env": "FIREWORKS_API_KEY",
            "family": "qwen",
        },
    }
    first, second = config["extract"]["models"]
    assert first["options"]["family"] == "kimi"
    assert second["provider"] == "openai"
    assert second["options"]["base_url"] == "https://api.groq.com/openai/v1"
    assert second["options"]["api_key_env"] == "GROQ_API_KEY"


def test_the_picker_filters_as_you_type():
    choices = [(f"{e['name']}  ({key})", key) for key, e in ENTRIES.items()]
    for typed, expected in (("fire", "fireworks-ai"), ("bedr", "amazon-bedrock"), ("groq", "groq")):
        with create_pipe_input() as typing:
            typing.send_text(f"{typed}\r")
            assert pick("provider", choices, input=typing, output=DummyOutput()) == expected


def test_cloud_providers_use_the_projects_sdk(monkeypatch: pytest.MonkeyPatch):
    sent: dict = {}

    class BedrockClient:
        def converse(self, **request):
            sent.update(request)
            reply = {"role": "assistant", "content": [{"text": '{"ok": true}'}]}
            return {"output": {"message": reply}, "usage": {"inputTokens": 7, "outputTokens": 3}}

    monkeypatch.setitem(
        sys.modules,
        "boto3",
        types.SimpleNamespace(client=lambda service, region_name: BedrockClient()),
    )
    entry = {"id": "amazon-bedrock", **ENTRIES["amazon-bedrock"]}
    serving = offer(
        "bedrock", entry, {"id": "anthropic.claude-x", **entry["models"]["anthropic.claude-x"]}
    )
    assert (serving.options, serving.packages) == ({"family": "claude"}, ("boto3",))

    judge = Judge(
        JudgeConfig(provider="bedrock", model="anthropic.claude-x", options=serving.options)
    )

    assert judge.ask("Reply with JSON only.", "Say ok.") == {"ok": True}
    assert sent["system"] == [{"text": "Reply with JSON only."}]
    assert sent["messages"] == [{"role": "user", "content": [{"text": "Say ok."}]}]
    assert (judge.input_tokens, judge.output_tokens) == (7, 3)


def test_check_names_a_missing_sdk():
    config = CasebenchConfig(judge=JudgeConfig(provider="bedrock", model="anthropic.claude-x"))

    [problem] = offline(config)

    assert problem.line() == "judge    failed: boto3 is not installed here"


def test_google_and_azure_use_the_projects_sdk(monkeypatch: pytest.MonkeyPatch):
    class Models:
        def generate_content(self, model, contents, config):
            assert (model, contents, config.system_instruction) == ("gemini-x", "Say ok.", "JSON.")
            usage = types.SimpleNamespace(prompt_token_count=5, candidates_token_count=2)
            return types.SimpleNamespace(text='{"ok": true}', usage_metadata=usage)

    genai = types.ModuleType("google.genai")
    genai.Client = lambda: types.SimpleNamespace(models=Models())  # type: ignore[attr-defined]
    genai.types = types.SimpleNamespace(  # type: ignore[attr-defined]
        GenerateContentConfig=lambda **settings: types.SimpleNamespace(**settings)
    )
    google = types.ModuleType("google")
    google.genai = genai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai.types)  # type: ignore[attr-defined]

    assert Judge(JudgeConfig(provider="google", model="gemini-x")).ask("JSON.", "Say ok.") == {
        "ok": True
    }

    class Completions:
        def create(self, model, messages):
            assert model == "my-deployment"
            message = types.SimpleNamespace(content='{"ok": true}')
            usage = types.SimpleNamespace(prompt_tokens=4, completion_tokens=1)
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=message)], usage=usage
            )

    import openai

    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=Completions()))
    monkeypatch.setattr(openai, "AzureOpenAI", lambda **settings: client)

    assert Judge(JudgeConfig(provider="azure", model="my-deployment")).ask("JSON.", "Say ok.") == {
        "ok": True
    }
