"""Stand-ins for a model API and a search backend, answering as the real ones do."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOOL_TURN = [
    {
        "type": "message_start",
        "message": {
            "model": "claude-sonnet-5-5",
            "usage": {"input_tokens": 120, "output_tokens": 1},
        },
    },
    {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "tool_use", "id": "toolu_1", "name": "search", "input": {}},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "input_json_delta", "partial_json": '{"query": '},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "input_json_delta", "partial_json": '"dismissal"}'},
    },
    {"type": "content_block_stop", "index": 0},
    {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 30}},
    {"type": "message_stop"},
]
FINAL_TURN = {
    "type": "message",
    "model": "claude-sonnet-5-5",
    "content": [{"type": "text", "text": "The dismissal is invalid."}],
    "usage": {"input_tokens": 200, "output_tokens": 40},
}


class Upstream(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/v1/messages") and body.get("stream"):
            self._send(
                "text/event-stream",
                "".join(
                    f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in TOOL_TURN
                ).encode(),
            )
        elif self.path.endswith("/v1/messages"):
            self._send("application/json", json.dumps(FINAL_TURN).encode())
        else:
            reply = {"result": [{"id": "tr-1", "score": 0.9}, {"id": "tr-2", "score": 0.7}]}
            self._send("application/json", json.dumps(reply).encode())

    def _send(self, content_type: str, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_upstream() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
