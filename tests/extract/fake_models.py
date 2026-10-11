"""Two extraction models behind the Anthropic Messages API, answering from fixtures."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tests.extract.decisions import DECISIONS, MODEL_A, MODEL_B

READINGS = {"model-a": MODEL_A, "model-b": MODEL_B}


class FakeModels(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text = body["messages"][0]["content"]
        decision = next(i for i, d in DECISIONS.items() if d[4] in text)
        reply = json.dumps(READINGS[body["model"]][decision], ensure_ascii=False)
        payload = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": reply}],
                "usage": {"input_tokens": 100, "output_tokens": 40},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_fake_models() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeModels)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
