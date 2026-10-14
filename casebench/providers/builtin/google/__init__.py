"""The google provider: Casebench's own calls to Gemini or Vertex AI, with google-genai."""

from typing import Any

from casebench.providers.interface import Completion, Message


class Provider:
    """The SDK reads the API key, or for Vertex AI its switch, project, location and Google
    sign-in, from the environment the project already set up (decision 0032).
    `reasoning_effort` is sent as `thinking_config.thinking_level` and `thinking_budget` as
    `thinking_config.thinking_budget`, as google-genai 2.30.1 names them (decision 0038)."""

    packages = ("google-genai",)
    api_key_env = None

    speaks = ("@ai-sdk/google", "@ai-sdk/google-vertex")

    def __init__(
        self,
        max_tokens: int | None = None,
        family: str = "gemini",
        reasoning_effort: str | None = None,
        thinking_budget: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.family = family
        self.reasoning_effort = reasoning_effort
        self.thinking_budget = thinking_budget
        self.temperature = temperature

    def config(self, system: str | None) -> dict[str, Any]:
        """The `GenerateContentConfig` fields; one not set is not sent."""
        thinking: dict[str, Any] = {}
        if self.reasoning_effort is not None:
            thinking["thinking_level"] = self.reasoning_effort.upper()
        if self.thinking_budget is not None:
            thinking["thinking_budget"] = self.thinking_budget
        values = {
            "system_instruction": system,
            "max_output_tokens": self.max_tokens,
            "temperature": self.temperature,
            "thinking_config": thinking or None,
        }
        return {name: value for name, value in values.items() if value is not None}

    def complete(self, messages: list[Message], model: str) -> Completion:
        # The project's own SDK, not a Casebench dependency.
        from google import genai  # pyright: ignore[reportAttributeAccessIssue]
        from google.genai import types  # pyright: ignore[reportMissingImports]

        client = genai.Client()
        system = "\n\n".join(m.content for m in messages if m.role == "system") or None
        reply = client.models.generate_content(
            model=model,
            contents="\n\n".join(m.content for m in messages if m.role != "system"),
            config=types.GenerateContentConfig(**self.config(system)),
        )
        usage = reply.usage_metadata
        return Completion(
            text=reply.text or "",
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
