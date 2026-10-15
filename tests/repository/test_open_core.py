"""The public repository: licence boundary, contribution gates, security posture, neutrality."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.repository.files import ROOT, load_yaml, run_lines, text, uses, workflow

EE_HEADER = "SPDX-License-Identifier: Elastic-2.0"
# Files under ee/ that are not source code carry no header.
UNMARKED = {"LICENSE", "README.md"}
SKIPPED = {"node_modules", "__pycache__", ".venv", "dist"}


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv to build the wheel")
def test_install_from_pypi(tmp_path: Path):
    # PyPI and its attestation are verified on the release; this proves the wheel
    # the release job builds installs on its own and exposes the command.
    subprocess.run(
        ["uv", "build", "--wheel", "--package", "casebench", "--out-dir", str(tmp_path / "dist")],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    wheel = next((tmp_path / "dist").glob("casebench-*.whl"))
    env = {
        **os.environ,
        "UV_TOOL_DIR": str(tmp_path / "tools"),
        "UV_TOOL_BIN_DIR": str(tmp_path / "bin"),
    }
    subprocess.run(["uv", "tool", "install", str(wheel)], check=True, capture_output=True, env=env)
    executable = "casebench.exe" if sys.platform == "win32" else "casebench"
    printed = subprocess.run(
        [str(tmp_path / "bin" / executable), "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert printed.stdout.startswith("casebench, version ")


def test_licence_boundary_visible():
    """`ee/` is under the Elastic License 2.0, word for word, and everything else under
    Apache-2.0 (decision 0057)."""
    licence = text("LICENSE")
    assert '"ee/" directory' in licence and "Elastic License 2.0" in licence
    assert "Apache License, Version 2.0" in licence
    ee = text("ee/LICENSE")
    assert "Elastic License 2.0" in ee
    assert "You may not provide the software to third parties as a hosted or managed" in ee

    for path in (ROOT / "ee").rglob("*"):
        parts = set(path.relative_to(ROOT / "ee").parts)
        if not path.is_file() or path.name in UNMARKED or parts & SKIPPED:
            continue
        head = path.read_text(encoding="utf-8").splitlines()[:5]
        assert any(EE_HEADER in line for line in head), path


def test_the_core_never_imports_ee():
    """The Apache-2.0 package works without `ee/` (decision 0057)."""
    for path in (ROOT / "casebench").rglob("*.py"):
        code = path.read_text(encoding="utf-8")
        assert "casebench_ee" not in code and "from ee" not in code, path


def test_contribution_gates():
    dco = run_lines(workflow("commits.yml")["jobs"]["commits"])
    assert "Signed-off-by" in dco

    matrix = workflow("ci.yml")["jobs"]["test"]["strategy"]["matrix"]["include"]
    assert {entry["os"] for entry in matrix} == {"ubuntu-latest", "macos-latest", "windows-latest"}

    # `ee/` takes no outside contributions for now, so no contributor agreement (0057).
    assert "takes no outside contributions" in text("CONTRIBUTING.md")


def test_security_posture():
    security = text("SECURITY.md")
    assert "private vulnerability reporting" in security
    assert "within 14 days" in security

    codeql = workflow("codeql.yml")["jobs"]["analyze"]
    assert any("codeql-action/analyze" in action for action in uses(codeql))
    scorecard = workflow("scorecard.yml")["jobs"]["analysis"]
    assert any("ossf/scorecard-action" in action for action in uses(scorecard))
    ecosystems = {u["package-ecosystem"] for u in load_yaml(".github/dependabot.yml")["updates"]}
    assert "github-actions" in ecosystems


def test_neutrality_terms_published():
    readme = text("README.md")
    assert "Frontier Legal, which maintains Casebench, publishes no rankings of products" in readme
    assert "never computes a score" in readme
    assert "reruns on your own corpus" in readme
