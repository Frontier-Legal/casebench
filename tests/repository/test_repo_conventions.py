"""How the repository works from the first commit: commits, releases, checks, supply chain."""

import re
import subprocess
import sys

import pytest

from tests.repository.files import (
    ROOT,
    all_workflows,
    load_json,
    load_yaml,
    run_lines,
    text,
    uses,
    workflow,
)

FULL_SHA = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def commit_check(message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "commitizen", "check", "--message", message],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def precommit_hook_ids() -> dict[str, dict]:
    config = load_yaml(".pre-commit-config.yaml")
    return {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}


def test_commit_messages_are_checked():
    rejected = commit_check("added the case model")
    assert rejected.returncode != 0
    assert "added the case model" in rejected.stdout + rejected.stderr

    assert commit_check("feat(core): add the case model").returncode == 0

    commits = workflow("commits.yml")["jobs"]["commits"]
    assert 'cz check --rev-range "$BASE..$HEAD"' in run_lines(commits)

    hooks = precommit_hook_ids()
    assert hooks["commitizen"]["stages"] == ["commit-msg"]
    assert "commit-msg" in load_yaml(".pre-commit-config.yaml")["default_install_hook_types"]


def test_a_release_is_a_tag():
    config = load_json("release-please-config.json")
    package = config["packages"]["."]
    assert package["release-type"] == "python"
    assert package["changelog-path"] == "CHANGELOG.md"
    assert load_json(".release-please-manifest.json")["."]

    jobs = workflow("release.yml")["jobs"]
    assert any("release-please-action" in action for action in uses(jobs["release-please"]))
    assert jobs["build"]["needs"] == "release-please"
    assert jobs["publish"]["needs"] == "build"
    assert "uv build" in run_lines(jobs["build"])
    assert any("pypa/gh-action-pypi-publish" in action for action in uses(jobs["publish"]))

    # Only the publish job may mint an OIDC token for Trusted Publishing.
    for name, job in jobs.items():
        has_token = job.get("permissions", {}).get("id-token") == "write"
        assert has_token == (name == "publish"), name


def test_versioning_says_what_breaks():
    config = load_json("release-please-config.json")
    assert config["bump-minor-pre-major"] is True
    assert config["bump-patch-for-minor-pre-major"] is False
    assert "0.x any minor release may break" in text("README.md")


@pytest.mark.xfail(strict=True, reason="one maintainer: a required review would block every merge")
def test_main_is_protected():
    ruleset = load_json(".github/rulesets/main.json")
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]

    rules = {rule["type"]: rule.get("parameters", {}) for rule in ruleset["rules"]}
    assert rules["pull_request"]["required_approving_review_count"] >= 1
    required = {
        check["context"] for check in rules["required_status_checks"]["required_status_checks"]
    }
    job_names = {job.get("name") for wf in all_workflows().values() for job in wf["jobs"].values()}
    assert required <= job_names
    assert {"deletion", "non_fast_forward"} <= rules.keys()
    assert "gitleaks" in precommit_hook_ids()


def test_the_same_checks_locally_and_in_ci():
    ci = workflow("ci.yml")["jobs"]
    lint = run_lines(ci["lint"])
    for command in ("ruff check", "ruff format --check", "pyright"):
        assert command in lint
    assert "zizmor" in run_lines(ci["workflows"])
    assert "uv run pytest" in run_lines(ci["test"])

    matrix = ci["test"]["strategy"]["matrix"]["include"]
    systems = {entry["os"] for entry in matrix}
    assert systems == {"ubuntu-latest", "macos-latest", "windows-latest"}
    linux = {entry["python"] for entry in matrix if entry["os"] == "ubuntu-latest"}
    assert linux == {"3.11", "3.12", "3.13", "3.14"}

    hooks = precommit_hook_ids()
    for hook in ("ruff-check", "ruff-format", "pyright", "pytest", "zizmor"):
        assert hook in hooks


def test_pinned_supply_chain():
    for name, wf in all_workflows().items():
        assert wf.get("permissions") in ({}, "read-all"), name
        for job_name, job in wf["jobs"].items():
            assert "permissions" in job, f"{name}:{job_name}"
            for action in uses(job):
                assert FULL_SHA.match(action), f"{name}:{job_name} uses {action}"
            for step in job.get("steps", []):
                if "actions/checkout" in step.get("uses", ""):
                    assert step["with"]["persist-credentials"] is False

    ecosystems = {
        update["package-ecosystem"] for update in load_yaml(".github/dependabot.yml")["updates"]
    }
    assert {"uv", "github-actions"} <= ecosystems


def test_a_contributor_finds_the_way_in():
    for path in (
        "AGENTS.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug.yml",
        ".github/ISSUE_TEMPLATE/need.yml",
        ".github/ISSUE_TEMPLATE/adapter.yml",
        ".github/pull_request_template.md",
        ".github/CODEOWNERS",
        "ADAPTERS.md",
        "CITATION.cff",
    ):
        assert (ROOT / path).is_file(), path

    contributing = text("CONTRIBUTING.md")
    assert "Conventional Commits" in contributing
    assert "feat(corpus): " in contributing
    assert "git commit -s" in contributing
    assert "test named after that scenario" in text(".github/pull_request_template.md")
    assert load_yaml("CITATION.cff")["cff-version"] == "1.2.0"
