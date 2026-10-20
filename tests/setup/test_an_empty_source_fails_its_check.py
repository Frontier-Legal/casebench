"""A source that answers but holds no document Casebench can read does not pass its check."""

import json
from pathlib import Path

from casebench.config import CasebenchConfig
from casebench.setup.checks import Status, live


def test_an_empty_source_fails_its_check(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    (tmp_path / "full").mkdir()
    record = {"id": "d1", "jurisdiction": "FR", "court": "Cour", "date": "2024-03-12", "text": "T."}
    (tmp_path / "full" / "d1.json").write_text(json.dumps(record), encoding="utf-8")
    config = CasebenchConfig.model_validate(
        {
            "corpora": {
                "empty": {"connector": "folder", "options": {"path": str(tmp_path / "empty")}},
                "full": {"connector": "folder", "options": {"path": str(tmp_path / "full")}},
            }
        }
    )

    found = {check.name: check for check in live(config)}

    assert found["corpus empty"].status is Status.FAILED
    assert "no document" in found["corpus empty"].detail
    assert "JSON" in found["corpus empty"].next
    assert found["corpus full"].status is Status.PASSED
