"""Send one model call through a provider.

The core, not the provider, does the sending.
"""

from collections.abc import Callable
from typing import Any

from casebench import keys
from casebench.providers.interface import Completion, HttpRequest, Message, ModelProvider

Send = Callable[[HttpRequest], tuple[int, Any]]


# RFC 9110 sections 15.5.2 and 15.5.4: the credentials are missing, wrong or not allowed.
REFUSED = (401, 403)


class MissingApiKey(RuntimeError):
    pass


class KeyRefused(RuntimeError):
    """The provider answered 401 or 403: the key is missing, wrong or not allowed there."""


def complete(
    provider: ModelProvider, messages: list[Message], model: str, send: Send
) -> Completion:
    """Read the key from the environment, build the request, send it, read the reply.
    An SDK provider makes its own call with the environment's credentials."""
    own_call = getattr(provider, "complete", None)
    if own_call is not None:
        return own_call(messages, model)
    api_key = keys.get(provider.api_key_env)
    if not api_key:
        raise MissingApiKey(f"set {provider.api_key_env} to call this provider")
    status, body = send(provider.request(messages, model, api_key))
    try:
        return provider.parse(status, body)
    except RuntimeError as error:
        # A refusal may echo the request; the key never reaches a message (decision 0043).
        said = keys.scrub(str(error), [provider.api_key_env])
        raise (KeyRefused if status in REFUSED else RuntimeError)(said) from None
