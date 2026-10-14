"""The openai provider: Chat Completions, at OpenAI or any OpenAI-compatible endpoint."""

from typing import Any

from casebench.providers.interface import Completion, HttpRequest, Message

# The openai 3.29.0 SDK honours a server's `retry-after` up to two minutes and does not retry
# past it (`MAX_RETRY_AFTER_DELAY`, read on 2026-10-14; decision 0037).
LONGEST_RETRY_AFTER_S = 120.0


class Provider:
    speaks = ("@ai-sdk/openai-compatible", "@ai-sdk/openai")

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        family: str = "openai",
        api_key_env: str = "OPENAI_API_KEY",
        max_tokens: int | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.family = family
        self.api_key_env = api_key_env
        self.max_tokens = max_tokens

    def request(self, messages: list[Message], model: str, api_key: str) -> HttpRequest:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if self.max_tokens is not None:
            body["max_completion_tokens"] = self.max_tokens
        return HttpRequest(
            method="POST",
            url=f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            body=body,
            longest_retry_after_s=LONGEST_RETRY_AFTER_S,
        )

    def parse(self, status: int, body: Any) -> Completion:
        if status != 200:
            raise RuntimeError(f"the API answered {status}: {body}")
        message = (body.get("choices") or [{}])[0].get("message") or {}
        usage = body.get("usage") or {}
        return Completion(
            text=message.get("content") or "",
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
