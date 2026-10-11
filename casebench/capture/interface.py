"""The capture parser contract: how to read one backend's traffic."""

from typing import Protocol, runtime_checkable

from casebench.capture.step import HttpExchange, Step


@runtime_checkable
class CaptureParser(Protocol):
    """Turns one backend's HTTP exchanges into normalised steps.

    A parser may also list `packages`: the SDKs whose calls it reads, as their package
    registries spell them, so `casebench init` can name the SDKs it finds in a project.
    """

    @property
    def hosts(self) -> list[str]:
        """The hosts whose traffic this parser reads, such as `api.example.com`."""
        ...

    def parse(self, exchange: HttpExchange) -> list[Step]:
        """The steps one exchange shows; an empty list if it shows none."""
        ...
