"""A licensed document API: bearer key, a search, documents in a universal work model."""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar
from urllib.parse import parse_qs, urlsplit

KEY = "test-key"
WORKS = {
    "101": {
        "court": "Yargıtay 9. Hukuk Dairesi",
        "decided": "2024-03-12",
        "text": "E. 2023/1234 K. 2024/567. İşçinin feshi geçersizdir. HÜKÜM: Bozulmasına.",
    },
    "102": {
        "court": "Yargıtay 22. Hukuk Dairesi",
        "decided": "2024-05-02",
        "text": "E. 2022/77 K. 2023/90. Kıdem tazminatı. HÜKÜM: Onanmasına.",
    },
    "103": {
        "court": None,
        "decided": "2024-06-01",
        "text": "4857 sayılı İş Kanunu madde 18: feshin geçerli sebebe dayandırılması.",
    },
}


def work(work_id: str) -> dict:
    data = WORKS[work_id]
    found = {
        "work_id": work_id,
        "jurisdiction": {"code": "TR", "level": "national"},
        "dates": [
            {"type": "published", "date": "2024-07-01"},
            {"type": "decided", "date": data["decided"]},
        ],
        "expressions": [{"language": "tr", "text": data["text"]}],
    }
    if data["court"]:
        found["issuers"] = [{"name": data["court"]}]
    return found


class DocumentApi(BaseHTTPRequestHandler):
    fetches: ClassVar[dict[str, int]] = {}
    searches: ClassVar[list[str]] = []

    def do_GET(self) -> None:
        if self.headers.get("Authorization") != f"Bearer {KEY}":
            return self._send(401, {"error": "missing_key"})
        url = urlsplit(self.path)
        if url.path == "/v1/search":
            DocumentApi.searches.append(parse_qs(url.query)["q"][0])
            words = set(re.findall(r"\w+", parse_qs(url.query)["q"][0].casefold()))
            hits = [
                i for i, w in WORKS.items() if words & set(re.findall(r"\w+", w["text"].casefold()))
            ]
            return self._send(200, {"results": [{"work": {"work_id": i}} for i in hits]})
        found = re.fullmatch(r"/v1/documents/(\d+)", url.path)
        if found and found.group(1) in WORKS:
            DocumentApi.fetches[found.group(1)] = DocumentApi.fetches.get(found.group(1), 0) + 1
            return self._send(200, work(found.group(1)))
        return self._send(404, {"error": "not_found"})

    def _send(self, status: int, body: dict) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def start_document_api() -> ThreadingHTTPServer:
    DocumentApi.fetches = {}
    DocumentApi.searches = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), DocumentApi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
