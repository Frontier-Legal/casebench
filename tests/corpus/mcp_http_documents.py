"""The MCP document server over Streamable HTTP, refusing every request without the test key."""

import sys
from typing import Any

import uvicorn

from tests.corpus.document_api import KEY
from tests.corpus.mcp_documents import server


def keyed(app: Any) -> Any:
    """What a commercial provider's hosted server does: no key, no answer."""

    async def guarded(scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"authorization")
            if sent != f"Bearer {KEY}".encode():
                await send({"type": "http.response.start", "status": 401, "headers": []})
                await send({"type": "http.response.body", "body": b"missing key"})
                return
        await app(scope, receive, send)

    return guarded


if __name__ == "__main__":
    app = server.streamable_http_app(stateless_http=True, json_response=True)
    uvicorn.run(keyed(app), host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
