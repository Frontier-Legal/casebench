"""Every Casebench format: the model that defines it and its current version."""

from dataclasses import dataclass

from pydantic import BaseModel

from casebench.core.case import FORMAT as CASE
from casebench.core.case import Case
from casebench.corpus.record import FORMAT as DOCUMENT
from casebench.corpus.record import DecisionRecord
from casebench.formats.version import FormatVersion, UnreadableFormat
from casebench.report.record import FORMAT as REPORT
from casebench.report.record import Report
from casebench.suites.freeze import FORMAT as SUITE
from casebench.suites.freeze import SuiteManifest


@dataclass(frozen=True)
class Format:
    """A format, and where a file of it says its version: in its own `format` field, or
    elsewhere (a suite's lines in the manifest, a document in its provider's profile)."""

    model: type[BaseModel]
    version: FormatVersion
    declares_itself: bool


FORMATS = {
    item.version.name: item
    for item in (
        Format(DecisionRecord, DOCUMENT, declares_itself=False),
        Format(Case, CASE, declares_itself=False),
        Format(SuiteManifest, SUITE, declares_itself=True),
        Format(Report, REPORT, declares_itself=True),
    )
}


def named(name: str) -> Format:
    if name not in FORMATS:
        raise UnreadableFormat(
            f"casebench.{name} is not a format; the formats are {sorted(FORMATS)}"
        )
    return FORMATS[name]
