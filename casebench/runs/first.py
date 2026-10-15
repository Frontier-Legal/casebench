"""The first `casebench run`: with no suite yet, it builds one and says what that costs first.

It extracts answer keys from a sample of the corpus, generates a suite from them, and runs it.
Each step keeps what it made, so a second run picks up where the first stopped (decision 0061).
"""

import sys
from pathlib import Path

import click

from casebench.config import CasebenchConfig
from casebench.corpus.corpora import Corpora
from casebench.extract.cli import DEFAULT_KEYS, extract_command
from casebench.extract.estimate import estimate
from casebench.extract.run import KEYS_FILE
from casebench.runs.log import RUN_FILE, RunLog
from casebench.suites.cli import generate_command
from casebench.suites.freeze import MANIFEST_FILE

FIRST = Path(".casebench") / "suites" / "first"
SUITE_ID = "first"
# Statute and precedent cases need the judge to find the documents the court cited.
TYPES, RESOLVED = "outcome", "outcome,statute,precedent"


def _keys_exist(keys_dir: Path) -> bool:
    return (keys_dir / KEYS_FILE).is_file()


def build(
    ctx: click.Context,
    config: CasebenchConfig,
    config_path: Path,
    suite_dir: Path,
    sample: int,
    cases: int,
    yes: bool,
) -> None:
    """Extract and generate the first suite, after the user agrees to what extraction costs."""
    if config.extract is None or not config.corpora:
        raise click.ClickException(
            "with no --suite, the first run builds one from the corpus: it needs `corpus:` and "
            "`extract:` in the config (casebench init sets both), or pass --suite"
        )
    name = next(iter(config.corpora))
    corpus = Corpora(config.corpora).only(name)
    keys_dir = DEFAULT_KEYS
    extracting = not _keys_exist(keys_dir)
    click.echo(f"no suite yet: the first run builds {suite_dir} from corpus {name}")
    if extracting:
        for line in estimate(corpus.connector.folder, config.extract.models, sample).lines():
            click.echo(f"  {line}")
    else:
        click.echo(f"  answer keys already in {keys_dir}; nothing to extract")
    click.echo(f"  then up to {cases} cases are generated and each is sent to your agent")
    if not yes:
        if not sys.stdin.isatty():
            raise click.ClickException("nothing was spent; pass --yes to build the suite and run")
        if not click.confirm("Go on?", default=False):
            raise click.Abort()
    if extracting:
        probe = config.corpora[name].probe
        ctx.invoke(
            extract_command,
            size=sample,
            config_path=config_path,
            queries=(probe,) if probe else (),
            out=keys_dir,
            max_concurrency=1,
            corpus_name=name,
            given=(),
            dry_run=False,
        )
    ctx.invoke(
        generate_command,
        keys_dir=keys_dir,
        types=RESOLVED if config.judge is not None else TYPES,
        count=cases,
        shares=(),
        after=None,
        stratify=None,
        suite_id=SUITE_ID,
        out=suite_dir,
        config_path=config_path,
    )


def is_built(suite_dir: Path) -> bool:
    return (suite_dir / MANIFEST_FILE).is_file()


def unfinished(runs_dir: Path, suite_id: str, suite_hash: str, cases: int) -> str | None:
    """The latest run of this suite that stopped before every case was answered."""
    if not runs_dir.is_dir():
        return None
    started = [f for f in runs_dir.iterdir() if (f / RUN_FILE).is_file()]
    for folder in sorted(started, key=lambda f: (f / RUN_FILE).stat().st_mtime, reverse=True):
        log = RunLog(folder)
        info = log.info
        if info.suite_id != suite_id or info.suite_hash != suite_hash:
            continue
        answered = {r.case_id for r in log.results()}
        return info.run_id if len(answered) < cases else None
    return None
