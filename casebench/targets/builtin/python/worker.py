"""A worker process: import the agent once, then answer one case at a time.

Run as `python -m casebench.targets.builtin.python.worker <entry> [<root>]`, where `root`
goes first on the import path. Messages travel on
standard input and output; the agent's own prints are sent to standard error.
"""

import asyncio
import os
import sys
from typing import Any

from casebench.capture import redirect
from casebench.capture.context import capturing
from casebench.capture.functions import STEP_FUNCTIONS, install, specs_from_environment
from casebench.targets.builtin.python.entry import accepted, call, load_entry
from casebench.targets.builtin.python.framing import encode, read_message
from casebench.targets.builtin.python.trace_context import agent_trace_context


def _jsonable(value: Any) -> Any:
    return value if isinstance(value, str | dict | list) or value is None else str(value)


def main(entry: str, root: str | None = None) -> None:
    replies = sys.stdout.buffer
    sys.stdout = sys.stderr
    if root:
        sys.path.insert(0, root)
    try:
        install(specs_from_environment(os.environ.get(STEP_FUNCTIONS)))
        redirect.install(os.environ.get(redirect.FOLLOW))
        function = load_entry(entry)
    except Exception as error:
        replies.write(encode({"ready": False, "error": f"{type(error).__name__}: {error}"}))
        replies.flush()
        return
    replies.write(encode({"ready": True}))
    replies.flush()
    loop = asyncio.new_event_loop()
    while (message := read_message(sys.stdin.buffer)) is not None:
        with capturing(message.get("case", "")) as captured:
            try:
                kwargs = accepted(function, message["inputs"])
                with agent_trace_context(message.get("traceparent")):
                    value = loop.run_until_complete(call(function, kwargs))
                reply: dict[str, Any] = {"value": _jsonable(value)}
            except Exception as error:
                reply = {"error": f"{type(error).__name__}: {error}"}
        reply["steps"] = [step.model_dump(mode="json") for step in captured.steps]
        replies.write(encode(reply))
        replies.flush()
    loop.close()


if __name__ == "__main__":
    main(*sys.argv[1:3])
