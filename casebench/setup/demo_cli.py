"""`casebench demo`: one case from the user's own corpus, asked and graded, shown as a table."""

import json
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from casebench import keys
from casebench.config import DEFAULT_CONFIG, load_config
from casebench.setup.demo import CITES, Demo, DemoNeeds, keep, plan, run_demo

# How much of the agent's answer the table shows; the whole answer is kept in answer.json.
SHOWN_ANSWER = 600
KINDS = {"outcome": "court's outcome", "statute": "relies on", "precedent": "relies on"}


def _rows(demo: Demo) -> list[dict[str, Any]]:
    """Each criterion: what it asks for, from the decision, and whether the answer met it."""
    facts = {fact.id: fact for fact in demo.case.reference.facts}
    met = {v.criterion_id: v for v in (demo.verdict.criteria if demo.verdict else [])}
    rows = []
    for criterion in demo.case.reference.criteria:
        if criterion.id == CITES:
            asked, value = "cites the decision", demo.citation
        else:
            fact = facts[criterion.derived_from[0]]
            asked, value = KINDS[fact.kind], fact.value
        verdict = met.get(criterion.id)
        rows.append(
            {
                "criterion": asked,
                "from the decision": value,
                "passed": None if verdict is None else verdict.passed,
                "quote": verdict.quote if verdict else None,
            }
        )
    return rows


def _report(demo: Demo) -> dict[str, Any]:
    answer = demo.result.output
    return {
        "decision": demo.citation,
        "question": demo.case.task.inputs.get("question"),
        "agent's answer": answer,
        "agent's error": demo.result.error,
        "score": demo.verdict.value if demo.verdict else None,
        "criteria": _rows(demo),
        "calls recorded": len([s for s in demo.result.steps if s.kind.value != "gap"]),
    }


def _shown(report: dict[str, Any]) -> None:
    console = Console()
    error = report["agent's error"]
    answer = report["agent's answer"] or f"no answer: {error}"
    if len(answer) > SHOWN_ANSWER:
        answer = answer[:SHOWN_ANSWER] + "…"
    head = Table(show_header=False, box=None, padding=(0, 2))
    head.add_row("[bold]decision[/]", report["decision"])
    head.add_row("[bold]question[/]", report["question"])
    head.add_row("[bold]agent[/]", answer)
    head.add_row("[bold]calls[/]", f"{report['calls recorded']} recorded")
    console.print(head)
    graded = Table(title="graded against the decision", title_justify="left")
    for column in ("criterion", "from the decision", "result", "where the answer says it"):
        graded.add_column(column, overflow="fold")
    for row in report["criteria"]:
        result = {True: "[green]✓ passed[/]", False: "[red]✗ failed[/]", None: "not graded"}
        graded.add_row(
            row["criterion"], row["from the decision"], result[row["passed"]], row["quote"] or ""
        )
    console.print(graded)
    if report["score"] is not None:
        console.print(f"score {report['score']:.2f}: the share of criteria met")


@click.command(name="demo")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="The result as JSON.")
def demo_command(config_path: Path, as_json: bool) -> None:
    """One case from your own corpus: a model drafts it from one decision, your agent answers
    it, and the judge grades the answer against what the court decided. It says first what it
    will spend, and spends no more (decision 0045)."""
    config = load_config(config_path)
    try:
        chosen = plan(config)
    except DemoNeeds as error:
        raise click.ClickException(str(error)) from error
    if not as_json:
        click.echo("This demo spends:")
        for line in chosen.lines():
            click.echo(f"  {line}")
        click.echo()
    try:
        demo = run_demo(config, chosen)
    except DemoNeeds as error:
        raise click.ClickException(str(error)) from error
    kept = keep(demo, config_path.resolve().parent / ".casebench" / "demo")
    report = _report(demo)
    if as_json:
        click.echo(keys.scrub(json.dumps(report, ensure_ascii=False, indent=2)))
        return
    _shown(report)
    click.echo(
        f"The case is a draft, written and graded by models with no lawyer between: kept in "
        f"{kept} for a lawyer to approve into a suite."
    )
