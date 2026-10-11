"""Which capture parsers read a host's traffic."""

from casebench.capture.interface import CaptureParser
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named


def parsers_for_host(host: str) -> list[CaptureParser]:
    """Every installed parser that declares the host, loaded only now."""
    kind = kind_named("parser")
    parsers: list[CaptureParser] = []
    for item in registry.available(kind):
        parser = registry.load(kind, item.name, item.source)()
        if host in parser.hosts:
            parsers.append(parser)
    return parsers
