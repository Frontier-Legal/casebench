"""Small HTTP services on loopback that answer as a test scripts them."""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

# What a handler gets: method, path, request headers and parsed JSON body (or None); what it
# returns: status, extra headers, and a JSON body.
Answer = Callable[[str, str, dict[str, str], Any], tuple[int, dict[str, str], Any]]


def serve(answer: Answer) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _answer(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else None
            status, headers, reply = answer(self.command, self.path, dict(self.headers), body)
            payload = json.dumps(reply).encode()
            self.send_response(status)
            for name, value in {"Content-Type": "application/json", **headers}.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = do_HEAD = _answer

        def log_message(self, format: str, *args: object) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def url(server: ThreadingHTTPServer, path: str = "") -> str:
    return f"http://127.0.0.1:{server.server_port}{path}"
