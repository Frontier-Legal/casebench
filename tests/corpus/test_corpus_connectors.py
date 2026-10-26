"""Every citation checked against the corpus: adding, checking and caching the corpus."""

import json
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import ConfigError, load_config
from casebench.corpus.binding import Corpus
from tests.corpus.document_api import KEY, DocumentApi, start_document_api

# What a person picks from the response; a script names it, since nothing is guessed (0043).
DOCUMENT_FIELDS = [
    "--field",
    "jurisdiction=$.jurisdiction.code",
    "--field",
    "court=$.issuers[0].name",
]
HTTP_FLAGS = [
    "--search-path",
    "/search",
    "--fetch-path",
    "/documents/{id}",
    "--header",
    "Authorization=Bearer ${DOC_KEY}",
    "--probe",
    "feshi",
    "--results",
    "$.results[*]",
    "--result-field",
    "id=$.work.work_id",
    *DOCUMENT_FIELDS,
    "--yes",
]
MCP_FIELDS = ["--results", "$.hits[*]", "--result-field", "id=$.document_id", *DOCUMENT_FIELDS]


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def add_http(config: Path, base: str):
    return invoke("corpus", "add", "http", "--base-url", base, "--config", str(config), *HTTP_FLAGS)


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.chdir(tmp_path)  # the cache lives in ./.casebench
    server = start_document_api()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_add_a_connector_from_the_command_line(api: str, tmp_path: Path):
    config = tmp_path / "casebench.yaml"

    added = add_http(config, api)

    assert added.exit_code == 0, added.output
    assert "$.expressions[0].text  text," in added.output
    corpus = yaml.safe_load(config.read_text(encoding="utf-8"))["corpora"]["127-0-0-1"]
    assert corpus["connector"] == "http"
    assert corpus["options"]["search_results"] == "$.results[*]"
    assert corpus["options"]["result_fields"]["id"] == "$.work.work_id"
    assert corpus["options"]["fields"]["id"] == "$.work_id"
    assert corpus["options"]["fields"]["text"] == "$.expressions[0].text"
    assert corpus["options"]["fields"]["court"] == "$.issuers[0].name"
    assert corpus["options"]["headers"] == {"Authorization": "Bearer ${DOC_KEY}"}

    again = add_http(config, api)  # a second store is added under its own name
    assert again.exit_code == 0, again.output
    corpora = yaml.safe_load(config.read_text(encoding="utf-8"))["corpora"]
    assert list(corpora) == ["127-0-0-1-2", "127-0-0-1"]
    taken = invoke(
        "corpus",
        "add",
        "http",
        "--base-url",
        api,
        "--name",
        "127-0-0-1",
        "--config",
        str(config),
        *HTTP_FLAGS,
    )
    assert taken.exit_code != 0 and "already has a corpus named 127-0-0-1" in taken.output

    mcp_config = tmp_path / "mcp.yaml"
    mcp_added = invoke(
        "corpus",
        "add",
        "mcp",
        "--command",
        f"{sys.executable} -m tests.corpus.mcp_documents",
        "--search-tool",
        "search",
        "--fetch-tool",
        "get_document",
        "--probe",
        "feshi",
        *MCP_FIELDS,
        "--yes",
        "--config",
        str(mcp_config),
    )
    assert mcp_added.exit_code == 0, mcp_added.output
    assert "get_document: One document in full." in mcp_added.output
    mcp_corpus = yaml.safe_load(mcp_config.read_text(encoding="utf-8"))["corpora"][
        "tests-corpus-mcp-documents"
    ]
    assert mcp_corpus["options"]["search_results"] == "$.hits[*]"
    assert mcp_corpus["options"]["result_fields"]["id"] == "$.document_id"


def test_connector_validated_on_a_sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    store = tmp_path / "decisions"
    store.mkdir()
    for n in range(250):
        (store / f"d{n}.json").write_text(
            json.dumps(
                {
                    "id": f"d{n}",
                    "jurisdiction": "xx",
                    "court": "Court",
                    "date": "2024-01-01",
                    "text": f"Decision {n}.",
                }
            ),
            encoding="utf-8",
        )
    config = tmp_path / "casebench.yaml"
    config.write_text(
        f"target: {{type: command, run: echo}}\ncorpus:\n  connector: folder\n"
        f"  options: {{path: '{store.as_posix()}'}}\n",
        encoding="utf-8",
    )

    first = invoke("corpus", "check", "--config", str(config))
    second = invoke("corpus", "check", "--config", str(config))

    assert first.exit_code == 0, first.output
    assert "sampled 200 documents (200 fetched, 0 from the cache)" in first.output
    assert "text          200/200 present" in first.output
    assert "sampled 200 documents (0 fetched, 200 from the cache)" in second.output
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        ".casebench",
        "casebench.yaml",
        "decisions",
    ]


def test_corpus_behind_a_licensed_api(api: str, tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    add_http(config, api)
    DocumentApi.fetches.clear()  # `corpus add` probes the store before the corpus exists

    first = invoke("corpus", "check", "--config", str(config), "--query", "feshi kıdem madde")
    second = invoke("corpus", "check", "--config", str(config), "--query", "feshi kıdem madde")

    assert first.exit_code == 0, first.output
    assert "sampled 3 documents (3 fetched, 0 from the cache)" in first.output
    assert "sampled 3 documents (0 fetched, 3 from the cache)" in second.output
    assert set(DocumentApi.fetches.values()) == {1}
    [(name, settings)] = load_config(config).corpora.items()
    assert Corpus(settings, name).search("E. 2023/1234 K. 2024/567", 1) == ["127-0-0-1:101"]


def test_corpus_check_searches_a_store_that_cannot_list_with_its_probe(api: str, tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    add_http(config, api)

    checked = invoke("corpus", "check", "--config", str(config))

    assert checked.exit_code == 0, checked.output
    assert "sampled 1 documents" in checked.output
    assert "search results, as the judge sees them to match a citation:" in checked.output


def test_any_http_api_or_mcp_server(api: str, tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    add_http(config, api)
    checked = invoke("corpus", "check", "--config", str(config), "--query", "feshi kıdem madde")
    assert "court         2/3 present" in checked.output
    assert "missing in some documents: court" in checked.output

    mcp_config = tmp_path / "mcp.yaml"
    invoke(
        "corpus",
        "add",
        "mcp",
        "--command",
        f"{sys.executable} -m tests.corpus.mcp_documents",
        "--search-tool",
        "search",
        "--fetch-tool",
        "get_document",
        "--probe",
        "feshi",
        *MCP_FIELDS,
        "--yes",
        "--config",
        str(mcp_config),
    )
    mcp_checked = invoke("corpus", "check", "--config", str(mcp_config), "--query", "feshi kıdem")
    assert mcp_checked.exit_code == 0, mcp_checked.output
    assert "sampled 2 documents" in mcp_checked.output


def test_the_agents_own_document_source_is_a_fine_corpus(tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    config.write_text(
        "target: {type: http, url: 'https://agent.firm.example/ask', body: {q: '{{question}}'},"
        " answer: $.answer}\n"
        "corpus: {connector: http, options: {base_url: 'https://docs.example/v1',"
        " search_path: /search, fetch_path: '/documents/{id}'}}\n",
        encoding="utf-8",
    )

    assert list(load_config(config).corpora) == ["corpus"]


def test_the_system_under_test_cannot_verify_itself(tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    config.write_text(
        "target: {type: http, url: 'https://agent.firm.example/ask', body: {q: '{{question}}'},"
        " answer: $.answer}\n"
        "corpus: {connector: http, options: {base_url: 'https://agent.firm.example',"
        " search_path: /ask, fetch_path: '/documents/{id}'}}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="citation checks must read raw decisions"):
        load_config(config)
    refused = invoke("corpus", "check", "--config", str(config))
    assert refused.exit_code != 0 and "never ask the system under test" in refused.output
