"""A judge behind the Anthropic Messages API that answers the citation and criteria questions the
way a careful model would, so the metrics' plumbing is tested without a real model."""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from casebench.judge import prompts
from tests.judge.matching import picks

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
# Second judges that see things differently: one never finds a claim supported or a criterion
# met, the other never recognises a cited document among the candidates.
DOUBTING = "doubting-judge"
LOST = "lost-judge"


def same_docket(citation: str, candidates: list[dict]) -> str | None:
    """The candidate whose matched passage carries the citation's docket number."""
    docket = re.search(r"E\. (\d{4}/\d+)", citation)
    for candidate in candidates:
        if docket and f"E. {docket.group(1)}" in (candidate.get("passage") or ""):
            return candidate["id"]
    return None


def graded(criterion: dict, answer: str, model: str) -> dict:
    """A criterion reads "Mentions <words>" and is met when the answer has those words; the
    doubting judge never finds a positive criterion met."""
    words = criterion["text"].removeprefix("Mentions ").casefold()
    met = words in answer.casefold() and not (model == DOUBTING and criterion["weight"] > 0)
    return {"id": criterion["id"], "met": met, "quote": answer if met else None}


def reply(system: str, user: str, model: str = "") -> object:
    if system == prompts.GRADE:
        answer, criteria = user.split("Answer:\n", 1)[1].split("\n\nCriteria:\n", 1)
        return [graded(criterion, answer, model) for criterion in json.loads(criteria)]
    if system == prompts.LIST_CITATIONS:
        return LISTED
    if system == prompts.MATCH and model == LOST:
        return picks(user, lambda citation, candidates: None)
    if system == prompts.WEIGH and model == DOUBTING:
        return {"supports": False, "quote": None, "reason": "the passage says something else"}
    if system == prompts.MATCH:
        return picks(user, same_docket)
    if system == prompts.WEIGH:
        document_id = re.search(r"Document (\S+) ", user).group(1)  # type: ignore[union-attr]
        quote = SUPPORTING.get(document_id)
        return {"supports": quote is not None, "quote": quote, "reason": "read the document"}
    if system == "Reply with JSON only.":
        return {"ok": True}
    raise AssertionError(f"unexpected judge prompt: {system[:40]}")


class FakeJudge(BaseHTTPRequestHandler):
    calls: list[str] = []  # noqa: RUF012

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeJudge.calls.append(body["system"][:20])
        asked = reply(body["system"], body["messages"][0]["content"], body.get("model", ""))
        text = json.dumps(asked, ensure_ascii=False)
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
