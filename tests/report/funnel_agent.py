"""An agent with no Casebench code: search, rerank, then one model call with what was kept."""

import json
import os
import sys
import urllib.request


def post(url: str, body: dict) -> dict:
    request = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json", "x-api-key": "k"}
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


question = sys.argv[1]
found = [hit["id"] for hit in post(os.environ["SEARCH_URL"] + "/search", {"q": question})["result"]]
kept = [
    hit["id"] for hit in post(os.environ["RERANK_URL"] + "/rerank", {"documents": found})["results"]
]
context = "\n".join(f"[{document_id}] ..." for document_id in kept)
reply = post(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    {
        "model": "claude-sonnet-5-5",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": f"{question}\n\nDocuments:\n{context}"}],
    },
)
print(reply["content"][0]["text"])
