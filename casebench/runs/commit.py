"""The commit a run ran at, so a baseline and a run name their code (decision 0048)."""

import os
import subprocess

# The variable GitHub Actions sets to the commit a workflow runs at.
GITHUB_SHA = "GITHUB_SHA"


def current_commit(given: str | None = None) -> str | None:
    """`given`, else GITHUB_SHA, else the commit checked out in the current folder, else none."""
    if given:
        return given
    if os.environ.get(GITHUB_SHA):
        return os.environ[GITHUB_SHA]
    try:
        found = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return found.stdout.strip() or None
