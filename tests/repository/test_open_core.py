"""The public repository: licence boundary, contribution gates, security posture, neutrality."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.repository.files import ROOT, load_yaml, run_lines, text, uses, workflow

EE_HEADER = "Licensed under the Casebench team server licence"


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
    licence = text("LICENSE")
    assert '"ee/" directory' in licence
    assert "Apache License, Version 2.0" in licence
    assert (ROOT / "ee" / "LICENSE").is_file()

    for path in (ROOT / "ee").rglob("*"):
        if path.is_file() and path.name != "LICENSE":
            assert EE_HEADER in path.read_text(encoding="utf-8"), path


@pytest.mark.xfail(strict=True, reason="the CLA text for ee/ awaits counsel review")
def test_contribution_gates():
    dco = run_lines(workflow("commits.yml")["jobs"]["commits"])
    assert "Signed-off-by" in dco

    matrix = workflow("ci.yml")["jobs"]["test"]["strategy"]["matrix"]["include"]
    assert {entry["os"] for entry in matrix} == {"ubuntu-latest", "macos-latest", "windows-latest"}

    cla = workflow("cla.yml")
    assert cla[True]["pull_request_target"]["paths"] == ["ee/**"]


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
