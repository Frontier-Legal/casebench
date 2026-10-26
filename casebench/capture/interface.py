"""The capture parser contract: how to read one backend's traffic."""

from typing import Protocol, runtime_checkable

from casebench.capture.step import HttpExchange, Step


@runtime_checkable
class CaptureParser(Protocol):
    """Turns one backend's HTTP exchanges into normalised steps.

    A parser may also list `packages`: the SDKs whose calls it reads, as their package
    registries spell them, so `casebench init` can name the SDKs it finds in a project.
    A parser may change a request before it is forwarded with `prepare(body)`, such as asking
    a stream for its usage. With `reads(url)`, which says from a call's URL alone whether it
    is the parser's API, the hook also runs for a call a Python agent sends to a host no route
    names.
    """

    @property
    def hosts(self) -> list[str]:
        """The hosts whose traffic this parser reads, such as `api.example.com`."""
        ...

    def parse(self, exchange: HttpExchange) -> list[Step]:
        """The steps one exchange shows; an empty list if it shows none."""
        ...
