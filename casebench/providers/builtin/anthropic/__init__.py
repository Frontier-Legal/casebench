"""The anthropic provider: Casebench's own calls through the Anthropic Messages API."""

from typing import Any

from casebench.providers.interface import Completion, HttpRequest, Message

# The Messages API version header its documentation requires.
API_VERSION = "2023-06-01"


class Provider:
    """`max_tokens` is required by the API and has no default here: set it in the judge's
    options, so the budget is the user's choice, not a number Casebench made up."""

    family = "anthropic"

    def __init__(
        self,
        base_url: str = "https://api.anthropic.com",
        max_tokens: int | None = None,
        api_key_env: str = "ANTHROPIC_API_KEY",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.api_key_env = api_key_env

    def request(self, messages: list[Message], model: str, api_key: str) -> HttpRequest:
        if self.max_tokens is None:
            raise ValueError("set max_tokens in the judge's options; the Messages API requires it")
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": m.role, "content": m.content} for m in messages if m.role != "system"
            ],
        }
        if system:
            body["system"] = system
        return HttpRequest(
            method="POST",
            url=f"{self.base_url}/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": API_VERSION},
            body=body,
        )

    def parse(self, status: int, body: Any) -> Completion:
        if status != 200:
            raise RuntimeError(f"the Anthropic API answered {status}: {body}")
        text = "".join(
            block.get("text", "")
            for block in body.get("content", [])
            if block.get("type") == "text"
        )
        usage = body.get("usage") or {}
        return Completion(
            text=text,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )
