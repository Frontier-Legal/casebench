"""An agent with no SDK and no tracing, as one in any language would be: it reads base URLs
from the environment, asks the model, runs the search tool it asked for, answers."""

import json
import os
import sys
import urllib.request


def post(url: str, body: dict) -> bytes:
    headers = {"Content-Type": "application/json", "x-api-key": "secret-key"}
    if os.environ.get("PASS_TRACE") and os.environ.get("TRACEPARENT"):
        headers["traceparent"] = os.environ["TRACEPARENT"]
    request = urllib.request.Request(url, json.dumps(body).encode(), headers)
    with urllib.request.urlopen(request) as response:
        return response.read()


model = os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages"
question = sys.argv[1]
asked = [{"role": "user", "content": question}]
stream = post(
    model, {"model": "claude-sonnet-5-5", "max_tokens": 512, "stream": True, "messages": asked}
).decode()
events = [json.loads(line[5:]) for line in stream.splitlines() if line.startswith("data:")]
tool_id = next(e["content_block"]["id"] for e in events if e["type"] == "content_block_start")
found = json.loads(
    post(os.environ["SEARCH_URL"] + "/collections/decisions/points/search", {"query": "dismissal"})
)
ids = ", ".join(point["id"] for point in found["result"])
asked += [
    {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "id": tool_id, "name": "search", "input": {"query": "dismissal"}}
        ],
    },
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": ids}]},
]
final = json.loads(
    post(model, {"model": "claude-sonnet-5-5", "max_tokens": 512, "messages": asked})
)
print(final["content"][0]["text"])
