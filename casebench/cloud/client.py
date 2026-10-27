"""The team server's sync routes, as an engineer's machine calls them with its API key (0059)."""

from pathlib import Path
from typing import Any

import httpx2

from casebench import envfiles, keys, network
from casebench.config import CloudConfig
from casebench.targets.placeholders import expand_env


class CloudError(RuntimeError):
    """What the server refused, in its words."""


def _key(cloud: CloudConfig, root: Path) -> str | None:
    """The shell's key, or one `keys:` named, or else the one value the project's .env files
    give it, held for this process's own calls (decision 0043)."""
    found = keys.get(cloud.key_env)
    if found:
        return found
    try:
        found = envfiles.agreed(cloud.key_env, root)
    except envfiles.Disagreement as differing:
        raise CloudError(
            f"{differing}; name the file it is read from under `keys:` in casebench.yaml"
        ) from None
    if found:
        keys.hold(cloud.key_env, found)
    return found


def connect(cloud: CloudConfig, root: Path) -> httpx2.Client:
    """A client for the server at `cloud.url`, whose `${NAME}`s are read as a corpus's base
    URL is (decision 0044), its key read as `_key` finds it; `root` is the project's folder,
    whose .env files are read."""
    key = _key(cloud, root)
    if not key:
        raise CloudError(
            f"no API key in {cloud.key_env}; an admin creates one on the Team page, and you set "
            "it in the environment or a .env file"
        )
    try:
        url = expand_env({"url": cloud.url})["url"]
    except KeyError as missing:
        raise CloudError(missing.args[0]) from None
    return network.client(
        base_url=url.rstrip("/"),
        headers={"Authorization": f"Bearer {key}"},
        timeout=120,
    )


def _answer(response: Any) -> Any:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        raise CloudError(str(detail or f"the server answered {response.status_code}"))
    return response.json()


class Cloud:
    """`http` has the server's address and the key; a test passes the server's own client."""

    def __init__(self, http: Any) -> None:
        self.http = http

    def push_suite(self, suite_id: str, files: dict[str, str]) -> dict[str, Any]:
        return _answer(self.http.post(f"/api/sync/suites/{suite_id}", json={"files": files}))

    def push_run(self, run_id: str, files: dict[str, str]) -> dict[str, Any]:
        return _answer(self.http.post(f"/api/sync/runs/{run_id}", json={"files": files}))

    def state(self, suites: list[str], runs: list[str]) -> dict[str, Any]:
        return _answer(self.http.post("/api/sync/state", json={"suites": suites, "runs": runs}))

    def invite(self, email: str, name: str, role: str) -> dict[str, Any]:
        return _answer(
            self.http.post("/api/team/users", json={"email": email, "name": name, "role": role})
        )
