"""An MCP server with a search tool and a fetch tool over the same documents."""

import json
import re

from mcp.server.mcpserver import MCPServer

from tests.corpus.document_api import WORKS, work

server = MCPServer("documents")


@server.tool()
def search(query: str) -> str:
    """Find documents whose text shares words with the query."""
    words = set(re.findall(r"\w+", query.casefold()))
    hits = [i for i, w in WORKS.items() if words & set(re.findall(r"\w+", w["text"].casefold()))]
    return json.dumps({"hits": [{"document_id": i} for i in hits]})


@server.tool()
def get_document(id: str) -> str:
    """One document in full."""
    return json.dumps(work(id), ensure_ascii=False)


if __name__ == "__main__":
    server.run()
