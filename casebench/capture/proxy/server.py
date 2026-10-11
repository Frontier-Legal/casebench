"""Run the proxy inside the Casebench process for the length of a run."""

import asyncio
import contextlib
from collections.abc import Iterator

import uvicorn
from starlette.applications import Starlette


class _InProcessServer(uvicorn.Server):
    """Leaves signal handling to the run, so Ctrl-C stops the run, not only the proxy."""

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


class ProxyServer:
    def __init__(self, app: Starlette, port: int = 0) -> None:
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        self.server = _InProcessServer(config)
        self.task: asyncio.Task[None] | None = None

    async def start(self) -> int:
        """Listen and return the port; port 0 lets the operating system choose a free one."""
        self.task = asyncio.create_task(self.server.serve())
        while not self.server.started:
            if self.task.done():
                self.task.result()
            await asyncio.sleep(0)
        return self.server.servers[0].sockets[0].getsockname()[1]

    async def stop(self) -> None:
        self.server.should_exit = True
        if self.task is not None:
            await self.task
            self.task = None
