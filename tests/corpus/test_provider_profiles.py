"""A provider's profile file sets up the corpus with no questions, or fails before writing."""

import json
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench import keys
from casebench.cli import main
from casebench.corpus.connectors.mcp import Connector as McpConnector
from tests.corpus.document_api import KEY, DocumentApi, start_document_api
from tests.corpus.profiles import FIELDS, http_options, profile

# A subprocess server is up within seconds on a CI runner; this is only a ceiling.
SERVER_START_S = 30.0


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[str]:
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.chdir(tmp_path)
    server = start_document_api()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


@pytest.fixture
def keyed_mcp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[str]:
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.chdir(tmp_path)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    root = Path(__file__).resolve().parents[2]
    process = subprocess.Popen(
        [sys.executable, "-m", "tests.corpus.mcp_http_documents", str(port)], cwd=root
    )
    deadline = time.monotonic() + SERVER_START_S
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            break
        except OSError:
            if time.monotonic() > deadline or process.poll() is not None:
                process.kill()
                raise
            time.sleep(0.1)
    yield f"http://127.0.0.1:{port}/mcp"
    process.terminate()
    process.wait()


def test_a_profile_sets_up_the_corpus_with_no_questions(api: str, tmp_path: Path):
    path = profile(tmp_path, "http", http_options(api))

    added = invoke("corpus", "add", "profile", str(path))

    assert added.exit_code == 0, added.output
    assert "Test Provider: searched 'feshi' and fetched document 101" in added.output
    # Its terms say nothing against keeping searches, so each one is paid once (0041).
    assert "Casebench keeps each search so it is paid once" in added.output
    written = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    corpus = written["corpora"]["provider"]
    assert corpus["connector"] == "http"
    assert corpus["profile"] == "provider.yaml"
    assert corpus["options"] == http_options(api)
    checked = invoke("corpus", "check", "--query", "feshi kıdem madde")
    assert checked.exit_code == 0, checked.output


def test_check_searches_a_store_added_from_a_profile_with_its_probe(api: str, tmp_path: Path):
    path = profile(tmp_path, "http", http_options(api))

    added = invoke("corpus", "add", "profile", str(path))
    checked = invoke("check", "--json")

    assert added.exit_code == 0, added.output
    written = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    assert written["corpora"]["provider"]["probe"] == "feshi"
    (corpus,) = [part for part in json.loads(checked.output)["parts"] if part["part"] == "corpus"]
    assert corpus["passed"], corpus


def test_init_sets_up_the_corpus_from_a_profile(api: str, tmp_path: Path):
    (tmp_path / "agent.py").write_text("def answer(q: str) -> str:\n    return 'x'\n", "utf-8")
    path = profile(tmp_path, "http", http_options(api))

    ran = invoke(
        "init",
        "--target",
        "python",
        "--entry",
        "agent.py:answer",
        "--profile",
        str(path),
        "--no-judge",
        "--no-extract",
        "--yes",
    )

    assert ran.exit_code == 0, ran.output
    assert "Test Provider: searched 'feshi'" in ran.output
    config = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    assert config["corpora"]["provider"]["profile"] == "provider.yaml"


def test_a_profile_whose_key_is_not_set_writes_nothing(
    api: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DOC_KEY")
    path = profile(tmp_path, "http", http_options(api))

    added = invoke("corpus", "add", "profile", str(path))

    assert added.exit_code == 1
    assert "DOC_KEY is set neither in this shell nor in a .env file that `keys:`" in added.output
    assert "name its file there as DOC_KEY: FILE" in added.output
    assert not (tmp_path / "casebench.yaml").exists()


def test_a_profile_key_kept_in_a_dot_env_file_that_keys_names_is_used(
    api: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("DOC_KEY")
    monkeypatch.setattr(keys, "_held", {})
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "eval.env").write_text(f"DOC_KEY={KEY}\n", encoding="utf-8")
    (tmp_path / "casebench.yaml").write_text("keys:\n  DOC_KEY: secrets/eval.env\n", "utf-8")
    path = profile(tmp_path, "http", http_options(api))

    added = invoke("corpus", "add", "profile", str(path))

    assert added.exit_code == 0, added.output
    assert "Test Provider: searched 'feshi' and fetched document 101" in added.output
    written = (tmp_path / "casebench.yaml").read_text(encoding="utf-8")
    assert "provider" in yaml.safe_load(written)["corpora"]
    assert KEY not in added.output and KEY not in written


def test_a_profile_that_does_not_match_the_provider_fails_before_writing(api: str, tmp_path: Path):
    path = profile(tmp_path, "http", http_options(api, {**FIELDS, "text": "$.body"}))

    added = invoke("corpus", "add", "profile", str(path))

    assert added.exit_code == 1
    assert "came back without text" in added.output
    assert not (tmp_path / "casebench.yaml").exists()


def test_init_stops_on_a_profile_it_cannot_read(api: str, tmp_path: Path):
    path = profile(tmp_path, "http", http_options(api), probe=None)

    ran = invoke("init", "--target", "python", "--entry", "agent.py:answer", "--profile", str(path))

    assert ran.exit_code == 1
    assert "is not a valid profile" in ran.output
    assert not (tmp_path / "casebench.yaml").exists()


def test_a_profile_reaches_a_hosted_mcp_server_that_needs_a_key(keyed_mcp: str, tmp_path: Path):
    options = {
        "url": keyed_mcp,
        "headers": {"Authorization": "Bearer ${DOC_KEY}"},
        "search_tool": "search",
        "search_arguments": {"query": "{text}"},
        "search_ids": "$.hits[*].document_id",
        "fetch_tool": "get_document",
        "fetch_arguments": {"id": "{id}"},
        "fields": FIELDS,
    }
    path = profile(tmp_path, "mcp", options)

    added = invoke("corpus", "add", "profile", str(path))

    assert added.exit_code == 0, added.output
    assert "fetched document 101" in added.output


def test_a_hosted_mcp_servers_address_may_name_a_variable(
    keyed_mcp: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MCP_URL", keyed_mcp)
    connector = McpConnector(
        url="${MCP_URL}",
        headers={"Authorization": "Bearer ${DOC_KEY}"},
        search_tool="search",
        search_ids="$.hits[*].document_id",
        fetch_tool="get_document",
    )
    try:
        assert connector.search("feshi", 1)
    finally:
        connector.close()


def test_a_provider_that_refuses_the_key_says_which_key(
    api: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOC_KEY", "a-wrong-key")
    path = profile(tmp_path, "http", http_options(api))

    added = invoke("corpus", "add", "profile", str(path))

    assert added.exit_code == 1
    assert "refused the live check (it answered 401); check that DOC_KEY holds" in added.output
    assert not (tmp_path / "casebench.yaml").exists()


def test_a_provider_whose_terms_forbid_a_local_copy_has_none_kept(api: str, tmp_path: Path):
    path = profile(tmp_path, "http", http_options(api), keep=[])

    added = invoke("corpus", "add", "profile", str(path))
    first = invoke("corpus", "check", "--query", "feshi")
    again = invoke("corpus", "check", "--query", "feshi")

    assert added.exit_code == 0, added.output
    assert "its terms let Casebench keep none, so each search is paid again" in added.output
    assert "keep no searches or documents on disk" in added.output
    written = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    assert written["corpora"]["provider"]["keep"] == []
    assert first.exit_code == 0, first.output
    assert again.exit_code == 0, again.output
    assert "(1 fetched, 0 from the cache)" in again.output  # read from the provider again
    assert DocumentApi.searches.count("feshi") == 3  # the live check and both checks
    cache = tmp_path / ".casebench" / "corpus-cache"
    assert not cache.exists() or not any(cache.rglob("*.json"))  # nothing written to disk
