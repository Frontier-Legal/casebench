"""The azure provider: Casebench's own calls to Azure OpenAI, with the project's openai SDK."""

from typing import Any

from casebench.providers.interface import Completion, Message


class Provider:
    """The SDK reads its endpoint, API version and key or Entra ID token from the environment
    the project already set up (decision 0032). The model is the deployment's name."""

    packages = ("openai",)
    api_key_env = None

    speaks = ("@ai-sdk/azure",)

    def __init__(
        self,
        endpoint: str | None = None,
        api_version: str | None = None,
        max_tokens: int | None = None,
        family: str = "azure",
    ) -> None:
        self.endpoint = endpoint
        self.api_version = api_version
        self.max_tokens = max_tokens
        self.family = family

    def complete(self, messages: list[Message], model: str) -> Completion:
        from openai import AzureOpenAI

        settings: dict[str, Any] = {}
        if self.endpoint:
            settings["azure_endpoint"] = self.endpoint
        if self.api_version:
            settings["api_version"] = self.api_version
        client = AzureOpenAI(**settings)
        request: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if self.max_tokens:
            request["max_completion_tokens"] = self.max_tokens
        reply = client.chat.completions.create(**request)
        usage = reply.usage
        return Completion(
            text=reply.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
