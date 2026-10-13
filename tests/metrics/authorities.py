"""A small corpus of statutes and decisions, and a judge that lists and matches their citations.

The court and the agent write the same authority differently; ALIASES says which document
each way of writing it means, as a careful judge would.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from casebench.judge import prompts

DOCUMENTS = {
    "law-4857-18": "4857 sayılı İş Kanunu madde 18. Feshin geçerli sebebe dayandırılması.",
    "law-1475-14": "1475 sayılı İş Kanunu madde 14. Kıdem tazminatı.",
    "law-6098-49": "6098 sayılı Türk Borçlar Kanunu madde 49. Haksız fiil.",
    "dec-9hd-2019-1": "Yargıtay 9. Hukuk Dairesi Esas 2019/1 Karar 2020/2. Fesih geçersizdir.",
}
ALIASES = {
    "4857 sayılı İş Kanunu m. 18": "law-4857-18",
    "İş K. md. 18": "law-4857-18",
    "1475 sayılı Kanun m. 14": "law-1475-14",
    "TBK m. 49": "law-6098-49",
    "Yargıtay 9. HD E. 2019/1 K. 2020/2": "dec-9hd-2019-1",
    "Yargıtay 9. Hukuk Dairesi 2019/1 E., 2020/2 K.": "dec-9hd-2019-1",
}
KINDS = {"dec-9hd-2019-1": "decision"}


def write_corpus(folder: Path) -> Path:
    folder.mkdir()
    for document_id, text in DOCUMENTS.items():
        (folder / f"{document_id}.json").write_text(
            json.dumps({"id": document_id, "jurisdiction": "TR", "text": text}, ensure_ascii=False),
            encoding="utf-8",
        )
    return folder


def reply(system: str, user: str) -> object:
    if system == prompts.LIST_CITATIONS:
        written = [w for w in ALIASES if w in user]
        written += [w for w in ("5510 sayılı Kanun m. 99",) if w in user]
        return [
            {"citation": w, "claim": "applies", "kind": KINDS.get(ALIASES.get(w, ""), "statute")}
            for w in written
        ]
    if system == prompts.MATCH:
        citation = user.split("\n", 1)[0].removeprefix("Citation: ")
        candidates = {c["id"] for c in json.loads(user.split("Candidates:\n", 1)[1])}
        wanted = ALIASES.get(citation)
        # The judge answers with a candidate's id as it was shown: qualified by its corpus.
        picked = next((c for c in sorted(candidates) if c.partition(":")[2] == wanted), None)
        return {"document_id": picked, "reason": "alias"}
    raise AssertionError(f"unexpected judge prompt: {system[:40]}")


class ResolvingJudge(BaseHTTPRequestHandler):
    calls: list[str] = []  # noqa: RUF012

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ResolvingJudge.calls.append(body["system"][:20])
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


def start_resolving_judge() -> ThreadingHTTPServer:
    ResolvingJudge.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), ResolvingJudge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
