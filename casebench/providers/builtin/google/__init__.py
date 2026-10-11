"""The google provider: Casebench's own calls to Gemini or Vertex AI, with google-genai."""

from casebench.providers.interface import Completion, Message


class Provider:
    """The SDK reads the API key, or for Vertex AI its switch, project, location and Google
    sign-in, from the environment the project already set up (decision 0032)."""

    packages = ("google-genai",)
    api_key_env = None

    speaks = ("@ai-sdk/google", "@ai-sdk/google-vertex")

    def __init__(self, max_tokens: int | None = None, family: str = "gemini") -> None:
        self.max_tokens = max_tokens
        self.family = family

    def complete(self, messages: list[Message], model: str) -> Completion:
        # The project's own SDK, not a Casebench dependency.
        from google import genai  # pyright: ignore[reportAttributeAccessIssue]
        from google.genai import types  # pyright: ignore[reportMissingImports]

        client = genai.Client()
        system = "\n\n".join(m.content for m in messages if m.role == "system") or None
        reply = client.models.generate_content(
            model=model,
            contents="\n\n".join(m.content for m in messages if m.role != "system"),
            config=types.GenerateContentConfig(
                system_instruction=system, max_output_tokens=self.max_tokens
            ),
        )
        usage = reply.usage_metadata
        return Completion(
            text=reply.text or "",
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
