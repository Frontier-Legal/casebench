"""A worker process: import the agent once, then answer one case at a time.

Run as `python -m casebench.targets.builtin.python.worker <entry>`. Messages travel on
standard input and output; the agent's own prints are sent to standard error.
"""

import asyncio
import sys
from typing import Any

from casebench.capture.context import capturing
from casebench.targets.builtin.python.entry import accepted, call, load_entry
from casebench.targets.builtin.python.framing import encode, read_message


def _jsonable(value: Any) -> Any:
    return value if isinstance(value, str | dict | list) or value is None else str(value)


def main(entry: str) -> None:
    replies = sys.stdout.buffer
    sys.stdout = sys.stderr
    function = load_entry(entry)
    loop = asyncio.new_event_loop()
    while (message := read_message(sys.stdin.buffer)) is not None:
        with capturing(message.get("case", "")) as captured:
            try:
                value = loop.run_until_complete(
                    call(function, accepted(function, message["inputs"]))
                )
                reply: dict[str, Any] = {"value": _jsonable(value)}
            except Exception as error:
                reply = {"error": f"{type(error).__name__}: {error}"}
        reply["steps"] = [step.model_dump(mode="json") for step in captured.steps]
        replies.write(encode(reply))
        replies.flush()
    loop.close()


if __name__ == "__main__":
    main(sys.argv[1])
