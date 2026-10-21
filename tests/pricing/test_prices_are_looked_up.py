"""A model's price comes from its seller's list, or the catalog's, never from casebench.yaml
unless someone wrote one there (decision 0069)."""

import os
from pathlib import Path
from urllib.parse import quote

import pytest
import yaml
from fastapi.testclient import TestClient

from casebench.config import CasebenchConfig, load_config
from casebench.judge.config import Price
from casebench.pricing import lookup
from casebench.pricing.priced import priced
from casebench.setup import catalog as model_catalog
from casebench.workbench.app import PERSON_HEADER, create_app
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store

SONNET = Price(input=3.0, output=15.0)
GPT = Price(input=2.0, output=8.0)
CONFIG = {
    "judges": [
        {
            "provider": "openai",
            "model": "anthropic/claude-sonnet-4.5",
            "options": {"base_url": "https://openrouter.ai/api/v1", "family": "claude"},
        },
        {
            "provider": "openai",
            "model": "home-model",
            "options": {"base_url": "http://gpu.internal/v1", "family": "home"},
            "price": {"input": 0.1, "output": 0.1},
        },
    ],
    "agent_models": [{"model": "gpt-4.1", "family": "gpt"}],
}


@pytest.fixture
def lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lookup, "_openrouter", lambda: {"anthropic/claude-sonnet-4.5": SONNET})
    monkeypatch.setattr(lookup, "_catalog", lambda: {"gpt-4.1": GPT, "claude-sonnet-4.5": SONNET})


def test_prices_come_from_the_sellers_lists(lists: None, tmp_path: Path):
    config = CasebenchConfig.model_validate(CONFIG)

    found = priced(config, lookup.lookup(tmp_path / "prices.json"))

    # OpenRouter's own list for the model it sells; the catalog for the agent's model; a price
    # someone wrote, for a model no list has, stays.
    assert found.judges[0].price == SONNET
    assert found.judges[1].price == Price(input=0.1, output=0.1)
    assert found.agent_models[0].price == GPT


def test_offline_prices_come_from_the_last_lists(
    lists: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    saved = tmp_path / "prices.json"
    lookup.lookup(saved)

    def unreachable() -> dict:
        raise OSError("no network")

    monkeypatch.setattr(lookup, "_openrouter", unreachable)
    monkeypatch.setattr(lookup, "_catalog", unreachable)
    found = priced(CasebenchConfig.model_validate(CONFIG), lookup.lookup(saved))

    assert found.agent_models[0].price == GPT


def test_a_price_is_never_written(lists: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "environ", os.environ.copy())
    lookup.lookup()  # the last lists, as a run before this one left them
    path = tmp_path / "casebench.yaml"
    written = {"judge": CONFIG["judges"][0], "agent_models": CONFIG["agent_models"]}
    path.write_text(yaml.safe_dump(written), encoding="utf-8")
    model = {"id": "gpt-4.1", "cost": {"input": 2.0, "output": 8.0}, "limit": {"context": 1000}}
    app = create_app(
        Workspace(tmp_path / "runs", [tmp_path]),
        Store(f"sqlite:///{tmp_path / 'db.sqlite'}"),
        ["t"],
        config=load_config(path),
        config_path=path,
        look_up_prices=True,
    )
    client = TestClient(app, base_url="http://t")
    me = {PERSON_HEADER: quote("A")}
    client.put("/api/me", json={"name": "A", "view": "engineering"}, headers=me)
    saved = client.put(
        "/api/settings/sections/workbench", json={"value": {"try_daily_limit_usd": 5}}, headers=me
    )

    # A model picked from the catalog is written without its price.
    assert "price" not in model_catalog.model_block("openai", model, {})
    assert saved.status_code == 200
    assert "price" not in path.read_text(encoding="utf-8")
    # The workbench prices the judge from OpenRouter's list all the same.
    (judge,) = client.get("/api/settings", headers=me).json()["models"]
    assert (judge["price_input"], judge["price_output"]) == (3.0, 15.0)
