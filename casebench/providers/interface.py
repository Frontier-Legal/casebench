"""The model provider contract for Casebench's own judge and extraction calls.

A provider is pure: it builds a request and reads a response. The core sends the
request, so the network allowlist applies to every provider and conformance runs
offline on recorded exchanges.
"""

from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from casebench.core.model import FrozenRecord


class Message(FrozenRecord):
    role: str
    content: str


class HttpRequest(FrozenRecord):
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None


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
