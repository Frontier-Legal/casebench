"""The partner report as one HTML file that opens from disk with no server, script or font.

Its styles are inline and it prints to A4 (decision 0054).
"""

from html import escape

from casebench.report.partner import (
    READING,
    PartnerReport,
    approval_lines,
    area_name,
    interval,
    percent,
)

STYLE = """
:root { color-scheme: light; --ink: #18181b; --muted: #71717a; --line: #e4e4e7;
  --soft: #f4f4f5; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
main { max-width: 60rem; margin: 0 auto; padding: 2.5rem 1rem 4rem; }
h1 { font-size: 1.6rem; margin: 0 0 .25rem; letter-spacing: -.01em; }
h2 { font-size: 1.15rem; margin: 2.25rem 0 .75rem; padding-bottom: .4rem;
  border-bottom: 1px solid var(--line); }
h3 { font-size: 1rem; margin: 1.5rem 0 .5rem; }
p { margin: .4rem 0; }
.muted { color: var(--muted); }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: .5rem; margin: 1rem 0; }
.fact { background: var(--soft); border-radius: .5rem; padding: .6rem .8rem; }
.fact b, .label { display: block; font-size: .75rem; text-transform: uppercase;
  letter-spacing: .04em; color: var(--muted); font-weight: 600; }
.wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { text-align: left; padding: .45rem .5rem; border-bottom: 1px solid var(--line);
  vertical-align: top; }
th { font-weight: 600; color: var(--muted); font-size: .8rem; }
td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.example { border: 1px solid var(--line); border-radius: .6rem; padding: .9rem 1rem;
  margin: .75rem 0; break-inside: avoid; }
.example .label { margin-top: .6rem; }
.example .text { white-space: pre-wrap; overflow-wrap: anywhere; }
.side { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.side > div + div { background: var(--soft); border-radius: .5rem; padding: 0 .8rem .6rem; }
@media (max-width: 40rem) { .side { grid-template-columns: 1fr; } }
footer { margin-top: 3rem; font-size: .8rem; color: var(--muted); overflow-wrap: anywhere; }
@page { size: A4; margin: 16mm; }
@media print {
  main { padding: 0; max-width: none; }
  h2 { break-after: avoid; }
  tr { break-inside: avoid; }
}
"""


def _cells(*values: str, numeric: tuple[int, ...] = ()) -> str:
    return "".join(
        f'<td class="n">{escape(v)}</td>' if n in numeric else f"<td>{escape(v)}</td>"
        for n, v in enumerate(values)
    )


def partner_html(report: PartnerReport) -> str:
    title = f"Casebench report: {report.suite_id}, run {report.run_id}"
    out = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title><style>{STYLE}</style></head><body><main>",
        f"<h1>{escape(report.suite_id)}</h1>",
        f'<p class="muted">How the AI under test answered the suite\'s cases, run '
        f"{escape(report.run_id)}, scored on {escape(report.scored_on)}.</p>",
        '<div class="facts">',
    ]
    for label, value in (
        ("AI under test", report.target),
        ("Cases approved", f"{report.approved} of {report.cases}"),
        ("Scored on", report.scored_on),
        ("Exported on", report.exported_on),
    ):
        out.append(f'<div class="fact"><b>{escape(label)}</b>{escape(value)}</div>')
    out.append("</div>")
    out.append("<h2>How to read it</h2>")
    out += [f"<p>{escape(line)}</p>" for line in READING]
    if report.left_out:
        out.append(
            f'<p class="muted">{report.left_out} answers to unreviewed cases are left out.</p>'
        )

    out.append("<h2>Errors</h2>")
    if report.error_rates:
        out.append('<div class="wrap"><table><thead><tr><th>Error</th><th>What it means</th>')
        out.append("<th>Rate</th><th>95% interval</th><th>Answers</th></tr></thead><tbody>")
        for rate in report.error_rates:
            cells = _cells(
                rate.error.capitalize(),
                f"The answer {rate.meaning}.",
                percent(rate.rate),
                interval(rate.low, rate.high),
                f"{len(rate.failing)} of {rate.n}",
                numeric=(2, 3, 4),
            )
            out.append(f"<tr>{cells}</tr>")
        out.append("</tbody></table></div>")
    else:
        out.append('<p class="muted">No metric in this run measures these errors.</p>')

    out.append("<h2>Results by task and practice area</h2>")
    out.append('<div class="wrap"><table><thead><tr><th>Task</th><th>Measure</th>')
    out.append("<th>Practice area</th><th>Cases</th><th>Score</th><th>95% interval</th>")
    out.append("</tr></thead><tbody>")
    for row in report.metrics:
        cells = _cells(
            row.task_type,
            row.name,
            area_name(row.practice_area),
            str(row.n),
            percent(row.mean),
            interval(row.low, row.high),
            numeric=(3, 4, 5),
        )
        out.append(f"<tr>{cells}</tr>")
    out.append("</tbody></table></div>")

    out.append("<h2>Worked examples</h2>")
    if not report.examples:
        out.append('<p class="muted">No answer had one of these errors.</p>')
    for example in report.examples:
        out.append('<section class="example">')
        out.append(
            f"<h3>{escape(example.error.capitalize())} · case {escape(example.case_id)} · "
            f"{escape(area_name(example.practice_area))}</h3>"
        )
        out.append(
            f'<div class="label">Question</div><div class="text">{escape(example.question)}</div>'
        )
        out.append('<div class="side"><div>')
        out.append(
            f'<div class="label">The AI\'s answer</div><div class="text">'
            f"{escape(example.answer)}</div>"
        )
        out.append("</div><div>")
        for shown in example.evidence:
            out.append(
                f'<div class="label">{escape(shown.label)}</div>'
                f'<div class="text">{escape(shown.text)}</div>'
            )
        out.append("</div></div></section>")

    out.append("<h2>Who approved the answer key</h2>")
    out += [f"<p>{escape(line)}</p>" for line in approval_lines(report)]
    out.append(
        f"<footer>Suite {escape(report.suite_id)}, hash {escape(report.suite_hash)}. Run "
        f"{escape(report.run_id)}. Casebench {escape(report.casebench_version)}.</footer>"
    )
    out.append("</main></body></html>")
    return "\n".join(out) + "\n"
