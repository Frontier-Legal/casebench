"""Keep every judge reply beside the run, so re-scoring reads it back instead of asking again."""

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from casebench import keys

MEMO_FILE = "judge.jsonl"


def memo_key(provider: str, model: str, system: str, user: str) -> str:
    asked = json.dumps([provider, model, system, user], ensure_ascii=False)
    return hashlib.sha256(asked.encode()).hexdigest()


class Memo:
    """One line per question: its key, the judge's parsed reply and, since decision 0051, the
    model and tokens of the call that made it, so the run can say what grading cost. Every
    line is scrubbed of keys before it is written (decision 0046)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.replies: dict[str, Any] = {}
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    self.replies[entry["key"]] = entry["reply"]

    def get(self, key: str) -> Any | None:
        return self.replies.get(key)

    def put(self, key: str, reply: Any, usage: dict[str, Any] | None = None) -> None:
        line = {"key": key, "reply": reply} | ({"usage": usage} if usage else {})
        with self.lock:
            self.replies[key] = reply
            with self.path.open("a", encoding="utf-8") as out:
                out.write(keys.scrub(json.dumps(line, ensure_ascii=False)) + "\n")


def usages(path: Path) -> list[dict[str, Any]]:
    """Each paid judge call kept beside the run: its provider, model and tokens, or nothing for
    a reply kept before calls recorded them."""
    if not path.is_file():
        return []
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [line.get("usage") or {} for line in lines]
