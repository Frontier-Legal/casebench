"""Ask the judge a question and read its JSON answer."""

import json
import re
from collections.abc import Callable
from typing import Any

from casebench.judge.config import JudgeConfig
from casebench.judge.memo import Memo, memo_key
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named
from casebench.providers.call import complete
from casebench.providers.interface import HttpRequest, Message, ModelProvider
from casebench.providers.send import send as send_over_http

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class JudgeReplyUnreadable(ValueError):
    """The judge did not answer with the JSON the prompt asked for."""


def read_json(text: str) -> Any:
    """The JSON in a reply, with or without a fenced block around it."""
    fenced = FENCE.search(text)
    candidate = (fenced.group(1) if fenced else text).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as error:
        raise JudgeReplyUnreadable(f"the judge's reply is not JSON: {text!r}") from error


class Judge:
    def __init__(
        self,
        config: JudgeConfig,
        send: Callable[[HttpRequest], tuple[int, Any]] = send_over_http,
        memo: Memo | None = None,
    ) -> None:
        self.config = config
        kind = kind_named("provider")
        self.provider: ModelProvider = registry.load(kind, config.provider, config.provider_source)(
            **config.options
        )
        self.send = send
        self.memo = memo
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def family(self) -> str:
        return self.provider.family

    def ask(self, system: str, user: str) -> Any:
        """A question already in the memo is answered from it, with no call."""
        key = memo_key(self.config.provider, self.config.model, system, user)
        if self.memo is not None and (kept := self.memo.get(key)) is not None:
            return kept
        self.calls += 1
        messages = [Message(role="system", content=system), Message(role="user", content=user)]
        completion = complete(self.provider, messages, self.config.model, self.send)
        self.input_tokens += completion.input_tokens or 0
        self.output_tokens += completion.output_tokens or 0
        reply = read_json(completion.text)
        if self.memo is not None:
            self.memo.put(key, reply)
        return reply
