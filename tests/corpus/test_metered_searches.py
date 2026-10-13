"""A provider that charges per search is paid once per query; a free store is searched afresh."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import load_config
from casebench.judge.config import JudgeConfig
from casebench.runs.dry_run import estimate
from tests.corpus.document_api import KEY, DocumentApi, start_document_api
from tests.corpus.profiles import http_options, profile
from tests.corpus.test_routing import case


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[str]:
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.chdir(tmp_path)
    server = start_document_api()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def connected(tmp_path: Path, api: str, metered: str) -> Path:
    path = profile(tmp_path, "http", http_options(api), metered=metered)
    added = invoke("corpus", "add", "profile", str(path))
    assert added.exit_code == 0, added.output
    DocumentApi.searches.clear()  # the live check while adding is not what is measured here
    return tmp_path / "casebench.yaml"


def test_a_provider_that_charges_per_search_is_paid_once_per_query(api: str, tmp_path: Path):
    config = connected(tmp_path, api, "search")

    first = invoke("corpus", "check", "--query", "feshi")
    second = invoke("corpus", "check", "--query", "feshi")

    assert yaml.safe_load(config.read_text("utf-8"))["corpora"]["provider"]["metered"] == "search"
    assert DocumentApi.searches == ["feshi"]
    assert "charges per search: this check may make 1 searches, 0 of them already kept" in (
        first.output
    )
    assert "1 of them already kept" in second.output
    assert "searched 0 times; the rest came from the cache" in second.output


def test_a_free_store_is_searched_afresh(api: str, tmp_path: Path):
    connected(tmp_path, api, "none")

    invoke("corpus", "check", "--query", "feshi")
    checked = invoke("corpus", "check", "--query", "feshi")

    assert DocumentApi.searches == ["feshi", "feshi"]  # documents added since would be found
    assert "charges per search" not in checked.output


def test_clearing_the_cache_lets_the_provider_be_searched_again(api: str, tmp_path: Path):
    connected(tmp_path, api, "search")
    invoke("corpus", "check", "--query", "feshi")

    cleared = invoke("corpus", "cache", "clear")
    invoke("corpus", "check", "--query", "feshi")

    assert "removed 1 cached documents and 1 cached searches" in cleared.output
    assert DocumentApi.searches == ["feshi", "feshi"]


def test_the_dry_run_counts_the_searches_already_kept(api: str, tmp_path: Path):
    config = connected(tmp_path, api, "search")
    invoke("corpus", "check", "--query", "feshi")
    # A judge is what makes the run search for citations at all.
    judged = load_config(config).model_copy(
        update={"judge": JudgeConfig(provider="anthropic", model="m")}
    )
    pending = [case().model_copy(update={"metrics": ["citation_integrity"]})]

    printed = "\n".join(estimate(pending, set(), judged).lines())

    assert "1 documents and 1 searches already cached cost no call" in printed
