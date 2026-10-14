"""`casebench check`: every check the config calls for, on the machine that will run it."""

import json
from pathlib import Path
from typing import Any

import click

from casebench import keys
from casebench.config import DEFAULT_CONFIG, load_config
from casebench.setup.advice import advice
from casebench.setup.checks import SETUP_SAMPLE, Check, Status, live, offline


def _part(item: Check) -> dict[str, Any]:
    """One part as a coding agent reads it; no message carries a key (decision 0044)."""
    return {
        "part": item.name,
        "status": item.status.value,
        "passed": item.status is Status.PASSED,
        "reason": keys.scrub(item.detail),
        "next": item.next if item.status is not Status.PASSED else "",
    }


@click.command(name="check")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option(
    "--query",
    "queries",
    multiple=True,
    help="A search that finds documents, for a store that cannot list them; the corpus's own "
    "probe search is run when none is given.",
)
@click.option(
    "--size",
    type=click.IntRange(min=1),
    default=SETUP_SAMPLE,
    show_default=True,
    help="Search results to take and documents to fetch; `casebench corpus check` samples more.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Each part's status, reason and next step as JSON, for a script or a coding agent.",
)
def check_command(config_path: Path, queries: tuple[str, ...], size: int, as_json: bool) -> None:
    """Check the corpus, the target and the judge from here; fail if any does not pass."""
    config = load_config(config_path)
    checks = offline(config)
    if not checks:
        checks = live(config, list(queries), size)
    passed = all(item.status is Status.PASSED for item in checks)
    if as_json:
        report = {
            "passed": passed,
            "parts": [_part(item) for item in checks],
            "advice": [keys.scrub(line) for line in advice(config)],
        }
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            click.echo(keys.scrub(item.line()))
        for line in advice(config):
            click.echo(f"could use {keys.scrub(line)}")
    if not passed:
        raise SystemExit(1)
