"""Length-prefixed JSON messages between Casebench and a worker, with no size limit."""

import json
from asyncio import StreamReader, StreamWriter
from typing import IO, Any


def encode(message: Any) -> bytes:
    """A decimal byte count, a newline, then the JSON."""
    body = json.dumps(message, ensure_ascii=False, default=str).encode("utf-8")
    return str(len(body)).encode("ascii") + b"\n" + body


def read_message(stream: IO[bytes]) -> Any | None:
    """The next message from a blocking stream; None when the stream has closed."""
    header = stream.readline()
    if not header:
        return None
    return json.loads(stream.read(int(header)))


async def read_message_async(stream: StreamReader) -> Any | None:
    header = await stream.readline()
    if not header:
        return None
    return json.loads(await stream.readexactly(int(header)))


async def send(stream: StreamWriter, message: Any) -> None:
    stream.write(encode(message))
    await stream.drain()
