"""Write the partner report as HTML, PDF or DOCX, chosen by the file's extension (decision 0054)."""

import re
from collections.abc import Callable
from pathlib import Path

from casebench.core.case import Case
from casebench.report.partner import PartnerReport, partner_report
from casebench.report.partner_docx import partner_docx
from casebench.report.partner_html import partner_html
from casebench.report.partner_pdf import partner_pdf
from casebench.runs.log import RunLog

FORMATS: dict[str, tuple[str, Callable[[PartnerReport], bytes]]] = {
    "html": ("text/html; charset=utf-8", lambda report: partner_html(report).encode("utf-8")),
    "pdf": ("application/pdf", partner_pdf),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        partner_docx,
    ),
}


class CannotExport(ValueError):
    """No such format, or a suite that is not the one the run ran."""


def exported(log: RunLog, cases: list[Case], suite_hash: str, kind: str) -> tuple[bytes, str]:
    """The report's bytes and media type. The suite must be the one the run ran, so the
    approvers named are those of the answer key it was scored against."""
    if kind not in FORMATS:
        raise CannotExport(f"export as {', '.join(FORMATS)}, not {kind}")
    if suite_hash != log.info.suite_hash:
        raise CannotExport(
            f"suite {log.info.suite_id} changed since run {log.info.run_id} ran it; export the "
            "report from a run of the suite as it is"
        )
    media, write = FORMATS[kind]
    return write(partner_report(log, cases)), media


def file_name(log: RunLog, kind: str) -> str:
    """Letters, digits, dots, hyphens and underscores only, so it fits any header."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", f"casebench-{log.info.suite_id}-{log.info.run_id}")
    return f"{stem}.{kind}"


def kind_of(path: Path) -> str:
    return path.suffix.lower().lstrip(".")
