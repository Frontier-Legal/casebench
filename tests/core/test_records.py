"""Records refuse what would make a score untrustworthy."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from casebench.core.case import Case, Criterion, Evidence, Fact, Reference, ReferenceSource
from casebench.suites.freeze import SuiteHashMismatch, freeze, load

EVIDENCE = Evidence(doc="d1", span=(0, 10))


def test_a_rewarded_criterion_needs_a_fact():
    with pytest.raises(ValidationError, match="rewards something no fact supports"):
        Criterion(id="c1", text="Concludes X", weight=5)


def test_a_criterion_cannot_weigh_nothing():
    with pytest.raises(ValidationError, match="weight 0"):
        Criterion(id="c1", text="Concludes X", weight=0, derived_from=["f1"])


def test_a_criterion_cites_only_known_facts():
    with pytest.raises(ValidationError, match="unknown facts"):
        Reference(
            source=ReferenceSource.LAWYER,
            facts=[Fact(id="f1", kind="issue", value="x", evidence=EVIDENCE)],
            criteria=[Criterion(id="c1", text="t", weight=2, derived_from=["f2"])],
        )


def test_unknown_fields_are_refused():
    with pytest.raises(ValidationError):
        Fact.model_validate(
            {"id": "f1", "kind": "k", "value": "v", "evidence": {"doc": "d"}, "x": 1}
        )


def test_criteria_are_written_with_their_source_facts_under_from():
    criterion = Criterion(id="c1", text="t", weight=2, derived_from=["f1"])
    written = criterion.model_dump(mode="json")
    assert written["from"] == ["f1"]
    assert Criterion.model_validate(written) == criterion


def test_an_edited_suite_is_refused(tmp_path: Path):
    case = Case.model_validate(
        {
            "id": "c-1",
            "task": {"type": "qa", "question": "Is the termination valid?"},
            "reference": {"source": "court", "facts": []},
            "metrics": ["criteria"],
        }
    )
    freeze("s1", [case], tmp_path)
    suite = tmp_path / "suite.jsonl"
    suite.write_text(suite.read_text(encoding="utf-8").replace("valid", "lawful"), encoding="utf-8")
    with pytest.raises(SuiteHashMismatch, match="was frozen as"):
        load(tmp_path)
