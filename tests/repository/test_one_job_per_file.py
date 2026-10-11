"""Every module names its one job in the first line of its docstring."""

import ast

from tests.repository.files import ROOT, text


def first_lines() -> dict[str, str | None]:
    found: dict[str, str | None] = {}
    for path in sorted((ROOT / "casebench").rglob("*.py")):
        docstring = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")))
        found[str(path.relative_to(ROOT))] = docstring.splitlines()[0] if docstring else None
    return found


def test_every_module_states_its_job():
    for module, line in first_lines().items():
        assert line, f"{module} has no docstring naming its job"
        sentence = line.rstrip(".")
        assert line.endswith("."), f"{module}: the first docstring line is not one sentence"
        assert ". " not in sentence, f"{module}: the first docstring line holds two sentences"


def test_the_contract_states_the_rule_without_a_line_count():
    contract = text("AGENTS.md")
    assert "One file has one job" in contract
    assert "lines" not in contract.split("## Rules")[1].split("\n2.")[0]
