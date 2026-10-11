"""A search backend, a reranker and a model API, as an agent's real ones would answer."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEARCHED = ["law-4857-18", "dec-9hd-2019-1", "law-1475-14"]
RERANKED = ["dec-9hd-2019-1"]
ANSWER = (
    "Yargıtay 9. Hukuk Dairesi 2019/1 E., 2020/2 K. decided this; the employer also owes "
    "damages under TBK m. 49."
)


class Upstream(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/search"):
            reply: object = {"result": [{"id": i} for i in SEARCHED]}
        elif self.path.endswith("/rerank"):
            reply = {"results": [{"id": i} for i in RERANKED if i in body["documents"]]}
        else:
            reply = {
                "type": "message",
                "model": "claude-sonnet-5-5",
                "content": [{"type": "text", "text": ANSWER}],
                "usage": {"input_tokens": 300, "output_tokens": 40},
            }
        payload = json.dumps(reply, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_funnel_upstream() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
