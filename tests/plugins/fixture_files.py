"""Files the plugin tests write: a working adapter, its samples, a mixed corpus."""

import json
import sys
from pathlib import Path

FR_ADAPTER = """import re
from datetime import date

from casebench.adapters.interface import Citation, CitationKind
from casebench.corpus.record import DecisionRecord

PATTERN = re.compile(r"Cass\\. (\\w+)\\., \\d{1,2} \\w+ \\d{4}, n° ([\\d-]+)")
LEVELS = {"Cour de cassation": "supreme", "Cour d'appel de Paris": "appellate"}


class Adapter:
    code = "fr"

    def citations(self, text: str) -> list[Citation]:
        return [
            Citation(text=m.group(0), start=m.start(), end=m.end(),
                     kind=CitationKind.DECISION, key=f"cass-{m.group(1)}-{m.group(2)}")
            for m in PATTERN.finditer(text)
        ]

    def operative_part(self, record: DecisionRecord) -> tuple[int, int] | None:
        start = record.text.find("PAR CES MOTIFS")
        return None if start < 0 else (start, len(record.text))

    def court_level(self, court: str) -> str | None:
        return LEVELS.get(court)

    def statute_version(self, key: str, on: date) -> str | None:
        return None
"""


def _decision(id_: str, court: str, text: str) -> dict:
    return {"id": id_, "jurisdiction": "fr", "court": court, "date": "2024-03-12", "text": text}


FR_SAMPLES = {
    "cassation.json": {
        "decision": _decision(
            "fr-1",
            "Cour de cassation",
            "Vu l'arrêt Cass. soc., 12 mars 2024, n° 22-12345. PAR CES MOTIFS, casse et annule.",
        ),
        "expected": {
            "citations": ["cass-soc-22-12345"],
            "operative_part_starts_with": "PAR CES MOTIFS",
            "court_level": "supreme",
        },
    },
    "appeal.json": {
        "decision": _decision(
            "fr-2", "Cour d'appel de Paris", "La cour confirme le jugement entrepris."
        ),
        "expected": {
            "citations": [],
            "operative_part_starts_with": "PAR CES MOTIFS",
            "court_level": "appellate",
        },
    },
}


def write_decisions(folder: Path) -> None:
    decisions = [
        {
            "id": "tr-1",
            "jurisdiction": "tr",
            "court": "Yargıtay 9. HD",
            "date": "2024-05-02",
            "text": "Davacı, E.2023/1 K.2024/2 sayılı karara dayanır. HÜKÜM: Bozulmasına.",
        },
        {
            "id": "nl-1",
            "jurisdiction": "nl",
            "court": "Hoge Raad",
            "date": "2024-06-07",
            "text": "Zie ECLI:NL:HR:2024:123. BESLISSING: De Hoge Raad verwerpt het beroep.",
        },
    ]
    for decision in decisions:
        (folder / f"{decision['id']}.json").write_text(
            json.dumps(decision, ensure_ascii=False), encoding="utf-8"
        )


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
