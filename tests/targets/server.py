"""A tiny agent behind HTTP: echoes the body it got and cites two decisions."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Agent(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:
        received = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        reply = {
            "data": {
                "text": f"echo {json.dumps(received, sort_keys=True)} "
                f"auth={self.headers.get('Authorization')}"
            },
            "sources": [{"ref": "E2023/1-K2024/2"}, {"ref": "E2022/7-K2023/9"}],
        }
        body = json.dumps(reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return None


def serve(port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Agent)


if __name__ == "__main__":
    serve(int(sys.argv[1])).serve_forever()
