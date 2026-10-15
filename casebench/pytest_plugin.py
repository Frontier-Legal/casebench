"""A Casebench suite as a pytest test, failing when the gate fails (decision 0048).

Mark a test `@pytest.mark.casebench(suite="suites/first", baseline="baselines/first")`. When
pytest runs it, the suite runs as `casebench run` would, with the project's casebench.yaml, and
the gate compares it with the baseline before the test's own body runs.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

MARKER = "casebench"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        f"{MARKER}(suite, baseline, config='casebench.yaml', runs_dir='.casebench/runs', "
        "include_unreviewed=False): run a Casebench suite and gate it against a baseline run",
    )


def _run_and_gate(options: dict[str, Any]) -> tuple[int, str]:
    from click.testing import CliRunner

    from casebench.cli import main

    runs = Path(options.get("runs_dir", ".casebench/runs"))
    run_id = f"pytest-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    ran = CliRunner().invoke(
        main,
        [
            "run",
            "--suite",
            str(options["suite"]),
            "--config",
            str(options.get("config", "casebench.yaml")),
            "--runs-dir",
            str(runs),
            "--run-id",
            run_id,
        ],
    )
    if ran.exit_code != 0:
        return ran.exit_code, f"the suite did not run:\n{ran.output}"
    unreviewed = ["--include-unreviewed"] if options.get("include_unreviewed") else []
    gated = CliRunner().invoke(
        main, ["gate", str(options["baseline"]), str(runs / run_id), *unreviewed]
    )
    return gated.exit_code, gated.output


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> None:
    """Runs before the test's body, which then runs as usual."""
    marker = pyfuncitem.get_closest_marker(MARKER)
    if marker is None:
        return
    code, report = _run_and_gate(dict(marker.kwargs))
    if code != 0:
        pytest.fail(f"Casebench gate failed (exit {code}):\n{report}", pytrace=False)
