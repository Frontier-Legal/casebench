"""An agent that passes no trace context and calls its model while every case is running."""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# How often to look for the other cases, and how long to wait for them, in seconds.
POLL = 0.01
WAIT = 30


def all_reached(stage: Path, expected: int) -> None:
    """Mark this process at a stage and wait until every case's process is there too."""
    stage.mkdir(exist_ok=True)
    (stage / str(os.getpid())).touch()
    deadline = time.monotonic() + WAIT
    while len(list(stage.iterdir())) < expected and time.monotonic() < deadline:
        time.sleep(POLL)


folder, expected = Path(sys.argv[1]), int(sys.argv[2])
all_reached(folder / "running", expected)
body = {"model": "claude-sonnet-5-5", "max_tokens": 512, "messages": []}
request = urllib.request.Request(
    os.environ["ANTHROPIC_BASE_URL"] + "/v1/messages",
    json.dumps(body).encode(),
    {"Content-Type": "application/json"},
)
with urllib.request.urlopen(request) as response:
    answer = json.loads(response.read())["content"][0]["text"]
all_reached(folder / "called", expected)
print(answer)
