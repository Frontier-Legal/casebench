"""Send one model call through a provider.

The core, not the provider, does the sending.
"""

import os
from collections.abc import Callable
from typing import Any

from casebench.providers.interface import Completion, HttpRequest, Message, ModelProvider

Send = Callable[[HttpRequest], tuple[int, Any]]


class MissingApiKey(RuntimeError):
    pass


def complete(
    provider: ModelProvider, messages: list[Message], model: str, send: Send
) -> Completion:
    """Read the key from the environment, build the request, send it, read the reply.
    An SDK provider makes its own call with the environment's credentials."""
    own_call = getattr(provider, "complete", None)
    if own_call is not None:
        return own_call(messages, model)
    api_key = os.environ.get(provider.api_key_env)
    if not api_key:
        raise MissingApiKey(f"set {provider.api_key_env} to call this provider")
    status, body = send(provider.request(messages, model, api_key))
    return provider.parse(status, body)
