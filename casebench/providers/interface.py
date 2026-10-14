"""The model provider contract for Casebench's own judge and extraction calls.

An HTTP provider is pure: it builds a request and reads a response. The core sends the
request, so the network allowlist applies to it and conformance runs offline on recorded
exchanges. An SDK provider instead has `complete(messages, model)`: it calls the vendor's
SDK already installed in the project, which reads the environment's credentials
(decision 0032).

A provider may name the public model catalog's API types it speaks (`speaks`); `casebench
init` then fills, from the catalog, the options its constructor takes: `base_url`,
`api_key_env`, `family`, and `max_tokens` where it requires one.
"""

from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from casebench.core.model import FrozenRecord


class Message(FrozenRecord):
    role: str
    content: str


class HttpRequest(FrozenRecord):
    """`longest_retry_after_s` is the longest wait a server may ask for before a retry, as the
    vendor's own SDK honours it; a longer one is not retried. None honours any wait."""

    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    longest_retry_after_s: float | None = None


class Completion(FrozenRecord):
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class ModelProvider(Protocol):
    @property
    def family(self) -> str:
        """The model family, used to warn when the judge and the target share one."""
        ...

    @property
    def api_key_env(self) -> str:
        """The environment variable the core reads the API key from."""
        ...

    def request(self, messages: list[Message], model: str, api_key: str) -> HttpRequest: ...

    def parse(self, status: int, body: Any) -> Completion: ...
