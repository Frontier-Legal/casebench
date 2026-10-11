"""An agent behind HTTP that Casebench starts: each question asks the model once."""

import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Agent(BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:
        question = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["question"]
        body = {
            "model": "claude-sonnet-5-5",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": question}],
        }
        request = urllib.request.Request(
            os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
            json.dumps(body).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            text = json.loads(response.read())["content"][0]["text"]
        payload = json.dumps({"answer": text}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Agent).serve_forever()
