"""`casebench push`, `pull` and `invite` on the engineer's machine (decision 0059); the round
trip with a team server is tested in ee/team_tests/test_push_pull.py."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from casebench.cli import main
from casebench.cloud.client import connect
from casebench.config import CloudConfig, load_config
from casebench.perimeter import hosts_of


def config(tmp_path: Path, cloud: str = "cloud:\n  url: https://casebench.firm.example\n") -> Path:
    path = tmp_path / "casebench.yaml"
    path.write_text(cloud, encoding="utf-8")
    return path


def test_push_needs_a_server_and_a_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CASEBENCH_CLOUD_KEY", raising=False)

    unnamed = CliRunner().invoke(main, ["push", "--config", str(config(tmp_path, "{}\n"))])
    keyless = CliRunner().invoke(main, ["pull", "--config", str(config(tmp_path))])

    assert unnamed.exit_code != 0 and "names no team server" in unnamed.output
    assert keyless.exit_code != 0 and "no API key in CASEBENCH_CLOUD_KEY" in keyless.output


def test_the_server_joins_the_allow_list(tmp_path: Path):
    hosts = hosts_of(load_config(config(tmp_path)))

    assert "casebench.firm.example" in hosts


def test_the_team_servers_address_may_name_a_variable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TEAM_URL", "https://casebench.firm.example/")
    monkeypatch.setenv("CASEBENCH_CLOUD_KEY", "cb-test-key")

    with connect(CloudConfig(url="${TEAM_URL}")) as client:
        assert str(client.base_url) == "https://casebench.firm.example"
