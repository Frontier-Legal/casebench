"""The bedrock provider: Casebench's own calls through Amazon Bedrock, with the project's boto3."""

from typing import Any

from casebench.providers.interface import Completion, Message


class Provider:
    """boto3 finds the region and credentials the way the project already does: environment,
    profile or role. Casebench signs nothing (decision 0032). `temperature` and `max_tokens`
    go in `inferenceConfig`; a model's reasoning settings exist on Bedrock only as that
    model's own fields, so they are given as `model_fields` and sent as
    `additionalModelRequestFields` unchanged (decision 0038)."""

    packages = ("boto3",)
    api_key_env = None

    speaks = ("@ai-sdk/amazon-bedrock",)

    def __init__(
        self,
        region: str | None = None,
        max_tokens: int | None = None,
        family: str = "bedrock",
        temperature: float | None = None,
        model_fields: dict[str, Any] | None = None,
    ) -> None:
        self.region = region
        self.max_tokens = max_tokens
        self.family = family
        self.temperature = temperature
        self.model_fields = model_fields

    def converse(self, messages: list[Message], model: str) -> dict[str, Any]:
        """The Converse request; a setting not given is not sent."""
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
        inference = {"maxTokens": self.max_tokens, "temperature": self.temperature}
        inference = {name: value for name, value in inference.items() if value is not None}
        if inference:
            request["inferenceConfig"] = inference
        if self.model_fields:
            request["additionalModelRequestFields"] = self.model_fields
        return request

    def complete(self, messages: list[Message], model: str) -> Completion:
        import boto3  # pyright: ignore[reportMissingImports]  # the project's own SDK

        client = boto3.client("bedrock-runtime", region_name=self.region)
        reply = client.converse(**self.converse(messages, model))
        blocks = reply["output"]["message"]["content"]
        usage = reply.get("usage") or {}
        return Completion(
            text="".join(block.get("text", "") for block in blocks),
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
        )
