"""`casebench push`, `pull` and `invite` on the engineer's machine (decision 0059); the round
trip with a team server is tested in ee/team_tests/test_push_pull.py."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from casebench import keys
from casebench.cli import main
from casebench.cloud import cli as cloud_cli
from casebench.cloud.client import Cloud, connect
from casebench.config import CloudConfig, load_config
from casebench.perimeter import hosts_of

KEY_VALUE = "cbk_not-a-real-key-but-shaped-like-one"
OTHER_VALUE = "cbk_another-key-shaped-like-the-first"


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


def test_the_team_servers_address_may_name_a_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("TEAM_URL", "https://casebench.firm.example/")
    monkeypatch.setenv("CASEBENCH_CLOUD_KEY", "cb-test-key")

    with connect(CloudConfig(url="${TEAM_URL}"), tmp_path) as client:
        assert str(client.base_url) == "https://casebench.firm.example"


def _pulled_with(seen: list[str]):
    """A pull that records the key the client was made with, and changes nothing."""

    def pulled(cloud: Cloud, workspace: object) -> SimpleNamespace:
        seen.append(cloud.http.headers["Authorization"])
        return SimpleNamespace(suites=[], reviews=0, preferences=0)

    return pulled


def test_a_cloud_key_kept_in_a_dot_env_file_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CASEBENCH_CLOUD_KEY", raising=False)
    monkeypatch.setattr(keys, "_held", {})
    (tmp_path / ".env").write_text(f"CASEBENCH_CLOUD_KEY={KEY_VALUE}\n", encoding="utf-8")
    seen: list[str] = []
    monkeypatch.setattr(cloud_cli, "pull", _pulled_with(seen))

    pulled = CliRunner().invoke(main, ["pull", "--config", str(config(tmp_path))])

    assert pulled.exit_code == 0, pulled.output
    assert seen == [f"Bearer {KEY_VALUE}"]
    assert KEY_VALUE not in pulled.output


def test_cloud_keys_that_differ_in_two_dot_env_files_stop_the_pull(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CASEBENCH_CLOUD_KEY", raising=False)
    monkeypatch.setattr(keys, "_held", {})
    (tmp_path / ".env").write_text(f"CASEBENCH_CLOUD_KEY={KEY_VALUE}\n", encoding="utf-8")
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval" / ".env").write_text(f"CASEBENCH_CLOUD_KEY={OTHER_VALUE}\n", "utf-8")
    seen: list[str] = []
    monkeypatch.setattr(cloud_cli, "pull", _pulled_with(seen))

    pulled = CliRunner().invoke(main, ["pull", "--config", str(config(tmp_path))])

    assert pulled.exit_code != 0 and not seen
    assert f".env (fingerprint {keys.fingerprint(KEY_VALUE)})" in pulled.output
    assert f"eval/.env (fingerprint {keys.fingerprint(OTHER_VALUE)})" in pulled.output
    assert "under `keys:` in casebench.yaml" in pulled.output
    assert KEY_VALUE not in pulled.output and OTHER_VALUE not in pulled.output
