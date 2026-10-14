"""Two extraction models behind the Anthropic Messages API, answering from fixtures."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

from tests.extract.decisions import DECISIONS, MODEL_A, MODEL_B

READINGS = {"model-a": MODEL_A, "model-b": MODEL_B}
# An effort the fake models do not offer; asking for it is refused, as a real API refuses.
UNOFFERED = "max"
CHECK_QUESTION = 'Reply with {"ok": true}.'


def reply_with(text: str) -> dict:
    return {
        "type": "message",
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 100, "output_tokens": 40},
    }


class FakeModels(BaseHTTPRequestHandler):
    """Keeps every request body, so a test can see what reached the provider."""

    bodies: ClassVar[list[dict]] = []

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeModels.bodies.append(body)
        if (body.get("output_config") or {}).get("effort") == UNOFFERED:
            message = f"effort {UNOFFERED} is not supported by this model"
            return self._send(400, {"error": {"message": message}})
        text = body["messages"][0]["content"]
        if text == CHECK_QUESTION:
            return self._send(200, reply_with('{"ok": true}'))
        decision = next(i for i, d in DECISIONS.items() if d[4] in text)
        reading = json.dumps(READINGS[body["model"]][decision], ensure_ascii=False)
        return self._send(200, reply_with(reading))

    def _send(self, status: int, body: dict) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_fake_models() -> ThreadingHTTPServer:
    FakeModels.bodies = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeModels)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
