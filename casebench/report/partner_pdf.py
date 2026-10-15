"""The partner report as an A4 PDF, in Noto Sans, which has letters such as ğ, ş and ı.

The PDF standard fonts lack them (decision 0054).
"""

from importlib import resources
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from casebench.report.partner import (
    READING,
    PartnerReport,
    approval_lines,
    area_name,
    interval,
    percent,
)

REGULAR, BOLD = "CasebenchSans", "CasebenchSans-Bold"
INK, MUTED, LINE, SOFT = (
    colors.HexColor("#18181b"),
    colors.HexColor("#71717a"),
    colors.HexColor("#e4e4e7"),
    colors.HexColor("#f4f4f5"),
)


def _fonts() -> None:
    if REGULAR in pdfmetrics.getRegisteredFontNames():
        return
    folder = resources.files("casebench.report") / "fonts"
    for name, file in ((REGULAR, "NotoSans-Regular.ttf"), (BOLD, "NotoSans-Bold.ttf")):
        with resources.as_file(folder / file) as path:
            pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(REGULAR, normal=REGULAR, bold=BOLD)


def _styles() -> dict[str, ParagraphStyle]:
    body = ParagraphStyle("body", fontName=REGULAR, fontSize=9.5, leading=13.5, textColor=INK)
    return {
        "title": ParagraphStyle("title", parent=body, fontName=BOLD, fontSize=20, leading=25),
        "h1": ParagraphStyle(
            "h1", parent=body, fontName=BOLD, fontSize=13, leading=17, spaceBefore=14, spaceAfter=6
        ),
        "h2": ParagraphStyle(
            "h2", parent=body, fontName=BOLD, fontSize=10.5, leading=14, spaceBefore=10
        ),
        "body": body,
        "muted": ParagraphStyle("muted", parent=body, textColor=MUTED),
        "label": ParagraphStyle(
            "label",
            parent=body,
            fontName=BOLD,
            fontSize=7,
            leading=9,
            textColor=MUTED,
            spaceBefore=5,
        ),
        "cell": ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11),
        "number": ParagraphStyle("number", parent=body, fontSize=8.5, leading=11, alignment=2),
        "head": ParagraphStyle(
            "head", parent=body, fontName=BOLD, fontSize=8, leading=10, textColor=MUTED
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    """Text as written: escaped, with its line breaks kept."""
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _table(
    header: list[str], rows: list[list[str]], widths: list[float], numeric: tuple[int, ...], s
) -> Table:
    data = [[_p(h, s["head"]) for h in header]] + [
        [_p(v, s["number"] if n in numeric else s["cell"]) for n, v in enumerate(row)]
        for row in rows
    ]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def partner_pdf(report: PartnerReport) -> bytes:
    _fonts()
    s = _styles()
    width = A4[0] - 32 * mm
    story: list = [
        _p(report.suite_id, s["title"]),
        _p(
            f"How the AI under test, {report.target}, answered the suite's cases: run "
            f"{report.run_id}, scored on {report.scored_on}, exported on {report.exported_on}. "
            f"{report.approved} of {report.cases} cases are approved by a lawyer.",
            s["muted"],
        ),
        _p("How to read it", s["h1"]),
    ]
    story += [_p(line, s["body"]) for line in READING]
    if report.left_out:
        story.append(_p(f"{report.left_out} answers to unreviewed cases are left out.", s["muted"]))

    story.append(_p("Errors", s["h1"]))
    if report.error_rates:
        story.append(
            _table(
                ["Error", "What it means", "Rate", "95% interval", "Answers"],
                [
                    [
                        rate.error.capitalize(),
                        f"The answer {rate.meaning}.",
                        percent(rate.rate),
                        interval(rate.low, rate.high),
                        f"{len(rate.failing)} of {rate.n}",
                    ]
                    for rate in report.error_rates
                ],
                [w * width for w in (0.2, 0.42, 0.1, 0.16, 0.12)],
                (2, 3, 4),
                s,
            )
        )
    else:
        story.append(_p("No metric in this run measures these errors.", s["muted"]))

    story.append(_p("Results by task and practice area", s["h1"]))
    story.append(
        _table(
            ["Task", "Measure", "Practice area", "Cases", "Score", "95% interval"],
            [
                [
                    row.task_type,
                    row.name,
                    area_name(row.practice_area),
                    str(row.n),
                    percent(row.mean),
                    interval(row.low, row.high),
                ]
                for row in report.metrics
            ],
            [w * width for w in (0.12, 0.32, 0.2, 0.1, 0.1, 0.16)],
            (3, 4, 5),
            s,
        )
    )

    story.append(_p("Worked examples", s["h1"]))
    if not report.examples:
        story.append(_p("No answer had one of these errors.", s["muted"]))
    for example in report.examples:
        block: list[Flowable] = [
            _p(
                f"{example.error.capitalize()} · case {example.case_id} · "
                f"{area_name(example.practice_area)}",
                s["h2"],
            ),
            _p("QUESTION", s["label"]),
            _p(example.question, s["body"]),
        ]
        side = [[_p("THE AI'S ANSWER", s["label"]), _p(example.answer, s["body"])], []]
        for shown in example.evidence:
            side[1] += [_p(shown.label.upper(), s["label"]), _p(shown.text, s["body"])]
        columns = Table([side], colWidths=[width / 2, width / 2])
        columns.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, -1), 0),
                    ("BACKGROUND", (1, 0), (1, -1), SOFT),
                ]
            )
        )
        block += [columns, Spacer(1, 4)]
        story.append(KeepTogether(block))

    story.append(_p("Who approved the answer key", s["h1"]))
    story += [_p(line, s["body"]) for line in approval_lines(report)]
    story += [
        Spacer(1, 12),
        _p(
            f"Suite {report.suite_id}, hash {report.suite_hash}. Run {report.run_id}. "
            f"Casebench {report.casebench_version}.",
            s["muted"],
        ),
    ]

    out = BytesIO()
    document = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{report.suite_id}: run {report.run_id}",
        author="Casebench",
    )
    document.build(story)
    return out.getvalue()
