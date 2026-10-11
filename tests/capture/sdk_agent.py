"""An agent built on the OpenAI SDK with no tracing: one tool, then a summary call."""

import json
import time
from typing import Any

from openai import OpenAI

client = OpenAI()
TOOLS: list[Any] = [
    {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
]


def search(query: str) -> str:
    return "tr-1, tr-2"


def answer(question: str) -> str:
    asked: list[Any] = [{"role": "user", "content": question}]
    first = client.chat.completions.create(model="gpt-5", messages=asked, tools=TOOLS)
    call: Any = (first.choices[0].message.tool_calls or [])[0]
    found = search(**json.loads(call.function.arguments))
    asked += [
        first.choices[0].message.model_dump(exclude_none=True),
        {"role": "tool", "tool_call_id": call.id, "content": found},
    ]
    draft = client.chat.completions.create(model="gpt-5", messages=asked, tools=TOOLS)
    time.sleep(0.05)  # work no call accounts for: shown as a gap
    summary = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": f"Summarise: {draft.choices[0].message.content}"}],
    )
    return summary.choices[0].message.content or ""
