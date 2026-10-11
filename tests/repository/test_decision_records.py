"""Architecture decisions are public records."""

import re
from pathlib import Path

import yaml

from tests.repository.files import ROOT, text

DECISIONS = ROOT / "docs" / "decisions"
REQUIRED_SECTIONS = (
    "## Context and problem statement",
    "## Considered options",
    "## Decision outcome",
    "### Consequences",
    "## Revisit when",
)


def records() -> list[Path]:
    return sorted(DECISIONS.glob("[0-9][0-9][0-9][0-9]-*.md"))


def front_matter(path: Path) -> dict:
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
    assert match, f"{path.name} has no front matter"
    return yaml.safe_load(match.group(1))


def title(path: Path) -> str:
    heading = re.search(r"^# (.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    assert heading, path.name
    return heading.group(1)


def test_the_first_decisions_are_on_record():
    titles = " | ".join(title(path).lower() for path in records())
    for topic in (
        "evaluation case",
        "opentelemetry genai",
        "open core",
        "never computes a score",
        "adapter is its own package",
        "no telemetry",
        "zero-code capture before decorators",
    ):
        assert topic in titles, topic

    index = text("docs/decisions/README.md")
    for path in records():
        body = path.read_text(encoding="utf-8")
        assert front_matter(path)["status"], path.name
        assert f"]({path.name})" in index, f"{path.name} is missing from the index"
        for section in REQUIRED_SECTIONS:
            assert section in body, f"{path.name} lacks {section}"


def test_a_material_change_carries_its_record():
    template = text(".github/pull_request_template.md")
    assert "## Decision record" in template
    for change in ("adds a dependency", "public interface", "storage format"):
        assert change in template
    assert "docs/decisions/" in template


def test_agents_and_humans_read_one_contract():
    contract = text("AGENTS.md")
    assert "gets a decision record under `docs/decisions/` before the code" in contract
    assert "No magic numbers" in contract
    assert "from a documented contract or from a measurement" in contract
    assert "Identifiers are English" in contract
    assert "exactly one test named after that scenario" in contract


def test_docs_have_one_home():
    # The repository can only check its own side: the design documents live here.
    design = ROOT / "docs" / "design"
    for name in ("architecture.md", "design.md", "harness-eval.md", "integrations.md"):
        assert (design / name).is_file(), name
    first_record = text("docs/decisions/0001-record-architecture-decisions.md")
    assert "[../design/](../design/)" in first_record


def test_superseding_is_explicit():
    numbers = {path.name[:4]: path for path in records()}
    assert len(numbers) == len(records()), "a record number is used twice"

    for path in records():
        status = str(front_matter(path)["status"])
        if status.startswith("superseded"):
            successor = re.search(r"superseded by (\d{4})", status)
            assert successor, f"{path.name} does not name its successor"
            assert successor.group(1) in numbers
            assert f"]({numbers[successor.group(1)].name})" in path.read_text(encoding="utf-8")

    assert "never deleted" in text("docs/decisions/README.md")
