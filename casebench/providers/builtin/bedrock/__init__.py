"""The bedrock provider: Casebench's own calls through Amazon Bedrock, with the project's boto3."""

from typing import Any

from casebench.providers.interface import Completion, Message


class Provider:
    """boto3 finds the region and credentials the way the project already does: environment,
    profile or role. Casebench signs nothing (decision 0032)."""

    packages = ("boto3",)
    api_key_env = None

    speaks = ("@ai-sdk/amazon-bedrock",)

    def __init__(
        self, region: str | None = None, max_tokens: int | None = None, family: str = "bedrock"
    ) -> None:
        self.region = region
        self.max_tokens = max_tokens
        self.family = family

    def complete(self, messages: list[Message], model: str) -> Completion:
        import boto3  # pyright: ignore[reportMissingImports]  # the project's own SDK

        client = boto3.client("bedrock-runtime", region_name=self.region)
        request: dict[str, Any] = {
            "modelId": model,
            "messages": [
                {"role": m.role, "content": [{"text": m.content}]}
                for m in messages
                if m.role != "system"
            ],
        }
        system = [{"text": m.content} for m in messages if m.role == "system"]
        if system:
            request["system"] = system
        if self.max_tokens:
            request["inferenceConfig"] = {"maxTokens": self.max_tokens}
        reply = client.converse(**request)
        blocks = reply["output"]["message"]["content"]
        usage = reply.get("usage") or {}
        return Completion(
            text="".join(block.get("text", "") for block in blocks),
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
        )
