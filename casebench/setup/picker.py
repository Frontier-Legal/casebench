"""A type-to-filter menu for the catalog's long lists."""

from typing import Any

import click
import questionary


def pick(
    message: str, choices: list[tuple[str, str]], default: str | None = None, **terminal: Any
) -> str:
    """Typing narrows the list; arrows move; Enter picks. `default` is the value the cursor
    starts on. `terminal` passes a test's input and output through to the menu."""
    question = questionary.select(
        message,
        choices=[questionary.Choice(title, value) for title, value in choices],
        use_search_filter=True,
        use_jk_keys=False,
        default=default,
        **terminal,
    )
    answer = question.unsafe_ask()
    if answer is None:
        raise click.Abort()
    return answer
