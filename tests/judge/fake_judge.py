"""A judge behind the Anthropic Messages API that answers the three citation questions the way
a careful model would, so the metric's plumbing is tested without a real model."""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from casebench.judge import prompts

LISTED = [
    {
        "citation": "Yargıtay 9. HD, E. 2023/1234 K. 2024/567",
        "claim": "A dismissal without a valid reason is invalid.",
    },
    {
        "citation": "Yargıtay 22. HD, E. 2022/77 K. 2023/90",
        "claim": "A dismissal without a valid reason is invalid.",
    },
    {
        "citation": "Yargıtay 3. HD, E. 2021/999 K. 2022/1",
        "claim": "Notice periods may be waived orally.",
    },
]
SUPPORTING = {"101": "İşçinin feshi geçersizdir."}


def reply(system: str, user: str) -> object:
    if system == prompts.LIST_CITATIONS:
        return LISTED
    if system == prompts.MATCH:
        docket = re.search(r"E\. (\d{4}/\d+)", user.split("Candidates:")[0])
        candidates = json.loads(user.split("Candidates:\n", 1)[1])
        for candidate in candidates:
            if docket and f"E. {docket.group(1)}" in candidate["opening"]:
                return {"document_id": candidate["id"], "reason": "same docket number"}
        return {"document_id": None, "reason": "no candidate carries that docket number"}
    if system == prompts.WEIGH:
        document_id = re.search(r"Document (\S+) ", user).group(1)  # type: ignore[union-attr]
        quote = SUPPORTING.get(document_id)
        return {"supports": quote is not None, "quote": quote, "reason": "read the document"}
    raise AssertionError(f"unexpected judge prompt: {system[:40]}")


class FakeJudge(BaseHTTPRequestHandler):
    calls: list[str] = []  # noqa: RUF012

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeJudge.calls.append(body["system"][:20])
        text = json.dumps(reply(body["system"], body["messages"][0]["content"]), ensure_ascii=False)
        payload = json.dumps(
            {
                "type": "message",
                "content": [{"type": "text", "text": text}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_fake_judge() -> ThreadingHTTPServer:
    FakeJudge.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeJudge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
