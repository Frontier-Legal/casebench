"""Show two extractions side by side: settings, agreement per field, time and cost (0038)."""

import json
import statistics
from pathlib import Path
from typing import Any

from casebench.extract.agreement import FIELDS
from casebench.extract.run import REPORT_FILE


def is_extraction(folder: Path) -> bool:
    return (folder / REPORT_FILE).is_file()


def _settings(report: dict[str, Any]) -> str:
    """Each model's settings, or that none was set and its provider's default applied."""
    shown = []
    for model in report["models"]:
        given = model.get("settings") or {}
        values = ", ".join(f"{k}={v}" for k, v in given.items()) or "provider default"
        shown.append(f"{model['model']}: {values}")
    return "; ".join(shown)


def _seconds(report: dict[str, Any]) -> str:
    each = (report.get("seconds") or {}).get("per_decision") or []
    return f"{statistics.median(each):.1f}s" if each else "-"


def _cost(report: dict[str, Any]) -> str:
    cost, read = report.get("cost"), report.get("read") or 0
    if cost is None:
        tokens = sum(m["input_tokens"] + m["output_tokens"] for m in report["models"])
        return f"unknown ({tokens} tokens)"
    return f"${cost:.2f} (${cost / read:.3f} a decision)" if read else f"${cost:.2f}"


def compare_lines(first: Path, second: Path) -> list[str]:
    """Counts beside the rates, since a small sample's rate alone says little."""
    reports = [json.loads((f / REPORT_FILE).read_text(encoding="utf-8")) for f in (first, second)]
    out = [f"A: {first}", f"   {_settings(reports[0])}", f"B: {second}"]
    out.append(f"   {_settings(reports[1])}")
    out.append(f"  {'':<22} {'A':>18} {'B':>18}")
    for name in FIELDS:
        cells = [
            f"{r['fields'][name]['agreed']}/{r.get('read', r['decisions'])} "
            f"({r['fields'][name]['rate']:.0%})"
            for r in reports
        ]
        out.append(f"  {name + ' agreement':<22} {cells[0]:>18} {cells[1]:>18}")
    rows = (
        ("keys kept", [str(r["keys"]) for r in reports]),
        ("median time a decision", [_seconds(r) for r in reports]),
        ("cost", [_cost(r) for r in reports]),
    )
    out += [f"  {label:<22} {a:>18} {b:>18}" for label, (a, b) in rows]
    return out
