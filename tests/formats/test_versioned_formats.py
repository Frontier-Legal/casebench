"""Casebench formats keep their promise: schemas match the code, released ones never change, and
files of every released version still validate (decision 0034)."""

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml
from click.testing import CliRunner

from casebench import __version__
from casebench.cli import main
from casebench.core.canonical import canonical_json, content_hash
from casebench.formats.files import SCHEMAS, file_hash, released, schema_path
from casebench.formats.registry import FORMATS
from casebench.formats.schema import schema_text
from casebench.report.record import FORMAT as REPORT
from casebench.suites.freeze import MANIFEST_FILE, SUITE_FILE, freeze, load
from tests.report.suites import outcome_case

EXAMPLES = Path(__file__).parent / "examples"


def example(name: str) -> dict[str, Any]:
    [path] = (EXAMPLES / name / "1.0").glob("*.json")
    return json.loads(path.read_text(encoding="utf-8"))


def written(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def validate(path: Path, *options: str):
    return CliRunner().invoke(main, ["validate", str(path), *options])


def test_the_shipped_schemas_match_the_code():
    for item in FORMATS.values():
        path = schema_path(item.version)
        assert path.is_file(), f"{path} is missing; run `casebench schema export`"
        assert path.read_text(encoding="utf-8") == schema_text(item.model), (
            f"{item.version} no longer matches its model: raise the format's version if "
            "that version is released, then run `casebench schema export`"
        )


def test_a_release_leaves_the_schemas_unchanged():
    """No schema holds Casebench's own version, which every release changes."""

    def values(node: Any):
        if isinstance(node, dict):
            for value in node.values():
                yield from values(value)
        elif isinstance(node, list):
            for value in node:
                yield from values(value)
        else:
            yield node

    for item in FORMATS.values():
        assert __version__ not in values(json.loads(schema_text(item.model))), item.version


def test_a_released_schema_never_changes():
    for name, digest in released().items():
        assert file_hash(SCHEMAS / name) == digest, f"{name} was released and has changed"


def test_files_of_every_released_version_still_validate():
    examples = sorted(p for p in EXAMPLES.glob("*/*/*") if p.suffix in (".json", ".yaml"))
    assert {path.parts[-3] for path in examples} == set(FORMATS), "a format has no example"
    for name in released():
        assert (EXAMPLES / Path(name).with_suffix("")).is_dir(), f"{name} has no examples"
    for path in examples:
        item = FORMATS[path.parts[-3]]
        data = yaml.safe_load(path.read_text(encoding="utf-8"))  # JSON is YAML too
        schema = json.loads(schema_path(item.version).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(data)
        ran = validate(path, "--format", f"casebench.{item.version.name}/{path.parts[-2]}")
        assert ran.exit_code == 0, ran.output


def test_schema_export_writes_one_file_per_format(tmp_path: Path):
    ran = CliRunner().invoke(main, ["schema", "export", "--into", str(tmp_path)])

    assert ran.exit_code == 0, ran.output
    files = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.json"))
    assert files == sorted(f"{i.version.name}/{i.version.file_name}" for i in FORMATS.values())


def test_validate_checks_the_rules_a_schema_cannot_hold(tmp_path: Path):
    case = example("case")
    case["reference"]["criteria"][0]["from"] = ["no-such-fact"]
    schema = json.loads(schema_path(FORMATS["case"].version).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(case)

    ran = validate(written(tmp_path / "case.json", case), "--format", "casebench.case/1.0")

    assert ran.exit_code == 1
    assert "cites unknown facts" in ran.output


def test_a_typo_in_a_known_version_fails_loudly(tmp_path: Path):
    report = example("report")
    report["scroes"] = report.pop("scores")

    ran = validate(written(tmp_path / "report.json", report))

    assert ran.exit_code == 1
    assert "scroes" in ran.output


def test_a_file_at_a_newer_minor_version_is_read_with_its_new_fields_named(tmp_path: Path):
    report = example("report")
    report["format"] = f"casebench.report/1.{REPORT.minor + 1}"
    report["reviewed_by"] = "a lawyer"

    ran = validate(written(tmp_path / "report.json", report))

    assert ran.exit_code == 0, ran.output
    assert "ignored reviewed_by" in ran.output


def test_a_file_at_another_major_version_is_refused(tmp_path: Path):
    report = example("report")
    report["format"] = "casebench.report/2.0"

    ran = validate(written(tmp_path / "report.json", report))

    assert ran.exit_code == 1
    assert "this Casebench reads casebench.report/1.x" in ran.output


def test_an_extension_is_keyed_by_a_domain(tmp_path: Path):
    case = example("case")
    case["extensions"] = {"notes": "not under a domain"}

    ran = validate(written(tmp_path / "case.json", case), "--format", "casebench.case/1.0")

    assert ran.exit_code == 1
    assert "extensions.notes" in ran.output


def test_a_frozen_suite_names_its_formats(tmp_path: Path):
    freeze("suite", [outcome_case(1, "reversed", "The appeal court found an error.")], tmp_path)

    manifest = json.loads((tmp_path / MANIFEST_FILE).read_text(encoding="utf-8"))
    assert (manifest["format"], manifest["case_format"]) == (
        "casebench.suite/1.0",
        "casebench.case/1.0",
    )
    ran = validate(tmp_path / SUITE_FILE)
    assert ran.exit_code == 0, ran.output


def test_a_suite_at_a_newer_minor_version_loads_with_its_hash(tmp_path: Path):
    freeze("suite", [outcome_case(1, "reversed", "The appeal court found an error.")], tmp_path)
    [line] = (tmp_path / SUITE_FILE).read_text(encoding="utf-8").splitlines()
    newer = {**json.loads(line), "difficulty": "hard"}
    (tmp_path / SUITE_FILE).write_text(json.dumps(newer) + "\n", encoding="utf-8")
    manifest = json.loads((tmp_path / MANIFEST_FILE).read_text(encoding="utf-8"))
    manifest["case_format"] = "casebench.case/1.1"
    manifest["content_hash"] = content_hash([canonical_json(newer)])
    written(tmp_path / MANIFEST_FILE, manifest)

    with pytest.warns(UserWarning, match="ignored difficulty"):
        loaded, cases = load(tmp_path)

    assert loaded.suite_id == "suite"
    assert [case.id for case in cases] == ["case-001"]


def test_export_refuses_to_change_a_released_schema(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("casebench.formats.schema_cli.is_released", lambda version: True)
    monkeypatch.setattr("casebench.formats.schema_cli.schema_text", lambda model: "{}\n")

    ran = CliRunner().invoke(main, ["schema", "export"])

    assert ran.exit_code == 1
    assert "is released and its schema never changes" in ran.output
    assert schema_path(FORMATS["document"].version).read_text(encoding="utf-8") != "{}\n"


def test_validate_finds_a_suite_whose_cases_changed_after_freezing(tmp_path: Path):
    freeze("suite", [outcome_case(1, "reversed", "The appeal court found an error.")], tmp_path)
    lines = (tmp_path / SUITE_FILE).read_text(encoding="utf-8")
    (tmp_path / SUITE_FILE).write_text(lines.replace("reversed", "upheld"), encoding="utf-8")

    ran = validate(tmp_path / MANIFEST_FILE)

    assert ran.exit_code == 1
    assert "was frozen as" in ran.output
