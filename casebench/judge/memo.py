"""Keep every judge reply beside the run, so re-scoring reads it back instead of asking again."""

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

MEMO_FILE = "judge.jsonl"


def memo_key(provider: str, model: str, system: str, user: str) -> str:
    asked = json.dumps([provider, model, system, user], ensure_ascii=False)
    return hashlib.sha256(asked.encode()).hexdigest()


class Memo:
    """One line per question: its key and the judge's parsed reply."""

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

    def put(self, key: str, reply: Any) -> None:
        with self.lock:
            self.replies[key] = reply
            with self.path.open("a", encoding="utf-8") as out:
                out.write(json.dumps({"key": key, "reply": reply}, ensure_ascii=False) + "\n")
