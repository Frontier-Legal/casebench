"""The team server's sync routes, as an engineer's machine calls them with its API key (0059)."""

from typing import Any

import httpx2

from casebench import keys, network
from casebench.config import CloudConfig


class CloudError(RuntimeError):
    """What the server refused, in its words."""


def connect(cloud: CloudConfig) -> httpx2.Client:
    key = keys.get(cloud.key_env)
    if not key:
        raise CloudError(
            f"no API key in {cloud.key_env}; an admin creates one on the Team page, and you set "
            "it in the environment or a .env file"
        )
    return network.client(
        base_url=cloud.url.rstrip("/"),
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
