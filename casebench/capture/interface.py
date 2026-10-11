"""The capture parser contract: how to read one backend's traffic."""

from typing import Protocol, runtime_checkable

from casebench.capture.step import HttpExchange, Step


@runtime_checkable
class CaptureParser(Protocol):
    """Turns one backend's HTTP exchanges into normalised steps."""

    @property
    def hosts(self) -> list[str]:
        """The hosts whose traffic this parser reads, such as `api.example.com`."""
        ...

    def parse(self, exchange: HttpExchange) -> list[Step]:
        """The steps one exchange shows; an empty list if it shows none."""
        ...
