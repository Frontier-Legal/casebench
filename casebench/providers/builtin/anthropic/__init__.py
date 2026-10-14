"""The anthropic provider: Casebench's own calls through the Anthropic Messages API."""

from typing import Any

from casebench.providers.interface import Completion, HttpRequest, Message

# The Messages API version header its documentation requires.
API_VERSION = "2023-06-01"


class Provider:
    """`max_tokens` is required by the API and has no default here: set it in the options,
    or let `casebench init` take the model's output limit from the catalog, so the budget is
    never a number Casebench made up. A server's `retry-after` is honoured however long it is,
    as the anthropic 1.13.0 SDK honours it (decision 0037). `reasoning_effort` is sent as
    `output_config.effort` and `thinking_budget` as `thinking.budget_tokens`; the Messages API
    takes no temperature (decision 0038)."""

    speaks = ("@ai-sdk/anthropic",)

    def __init__(
        self,
        max_tokens: int,
        base_url: str = "https://api.anthropic.com",
        api_key_env: str = "ANTHROPIC_API_KEY",
        family: str = "anthropic",
        reasoning_effort: str | None = None,
        thinking_budget: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/").removesuffix("/v1")  # requests add /v1 themselves
        self.max_tokens = max_tokens
        self.api_key_env = api_key_env
        self.family = family
        self.reasoning_effort = reasoning_effort
        self.thinking_budget = thinking_budget

    def request(self, messages: list[Message], model: str, api_key: str) -> HttpRequest:
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
        if self.reasoning_effort is not None:
            body["output_config"] = {"effort": self.reasoning_effort}
        if self.thinking_budget is not None:
            body["thinking"] = {"type": "enabled", "budget_tokens": self.thinking_budget}
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
