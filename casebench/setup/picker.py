"""Ask a question with options: a type-to-filter menu on a terminal, numbered lines elsewhere."""

import sys
from typing import Any

import click
import questionary
from questionary import Style

# The onboarding's colours (decision 0043): the question marker and the highlighted choice.
STYLE = Style(
    [
        ("qmark", "fg:#60a5fa bold"),
        ("question", "bold"),
        ("pointer", "fg:#a78bfa bold"),
        ("highlighted", "fg:#a78bfa bold"),
        ("answer", "fg:#22d3ee bold"),
        ("instruction", "fg:#6b7280"),
    ]
)
MARK = "◆"


def interactive() -> bool:
    """A person at a terminal, who can use arrows and type to filter."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _numbered(message: str, choices: list[tuple[str, str]], default: str | None) -> str:
    """Without a terminal: the options numbered, answered by a number or the value itself."""
    click.echo(message)
    for number, (title, _) in enumerate(choices, start=1):
        click.echo(f"  {number}. {title}")
    values = [value for _, value in choices]
    first = values.index(default) + 1 if default in values else 1
    while True:
        answer = click.prompt("number", default=str(first)).strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return values[int(answer) - 1]
        if answer in values:
            return answer
        click.echo(f"choose 1 to {len(choices)}")


def pick(
    message: str, choices: list[tuple[str, str]], default: str | None = None, **terminal: Any
) -> str:
    """Typing narrows the list; arrows move; Enter picks. `default` is the value the cursor
    starts on. `terminal` passes a test's input and output through to the menu."""
    if not terminal and not interactive():
        return _numbered(message, choices, default)
    question = questionary.select(
        message,
        choices=[questionary.Choice(title, value) for title, value in choices],
        use_search_filter=True,
        use_jk_keys=False,
        default=default,
        qmark=MARK,
        style=STYLE,
        instruction="(type to filter)",
        **terminal,
    )
    answer = question.unsafe_ask()
    if answer is None:
        raise click.Abort()
    return answer


def text(message: str, default: str | None = None, secret: bool = False) -> str:
    """A line of text, with the same look as the menus."""
    if not interactive():
        return click.prompt(message, default=default, hide_input=secret)
    ask = questionary.password if secret else questionary.text
    answer = ask(message, default=default or "", qmark=MARK, style=STYLE).unsafe_ask()
    if answer is None:
        raise click.Abort()
    return answer


def confirm(message: str, default: bool = True) -> bool:
    if not interactive():
        return click.confirm(message, default=default)
    answer = questionary.confirm(message, default=default, qmark=MARK, style=STYLE).unsafe_ask()
    if answer is None:
        raise click.Abort()
    return bool(answer)
