"""A national model API no OpenTelemetry instrumentor knows, answering over HTTP."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class NationalApi(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.rfile.read(int(self.headers["Content-Length"]))
        payload = json.dumps({"output": "Geçersiz.", "usage": {"in": 812, "out": 96}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_national_api() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), NationalApi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
