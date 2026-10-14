"""Draw onboarding in the terminal: the logo, each step, notes, spinners and the review."""

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from casebench import __version__

# One glyph per letter, four rows each, in the shape of figlet's "small" font.
GLYPHS = {
    "C": ["  ___ ", " / __|", "| (__ ", " \\___|"],
    "A": ["   _   ", "  /_\\  ", " / _ \\ ", "/_/ \\_\\"],
    "S": [" ___ ", "/ __|", "\\__ \\", "|___/"],
    "E": [" ___ ", "| __|", "| _| ", "|___|"],
    "B": [" ___ ", "| _ )", "| _ \\", "|___/"],
    "N": [" _  _ ", "| \\| |", "| .` |", "|_|\\_|"],
    "H": [" _  _ ", "| || |", "| __ |", "|_||_|"],
}
# Each row of the logo a shade further from violet to cyan.
SHADES = ("#a78bfa", "#818cf8", "#60a5fa", "#22d3ee")
TAGLINE = "legal accuracy, measured against real court decisions"
GUTTER = "│"


def console() -> Console:
    """Made per call, so it writes wherever stdout points now, as tests swap it."""
    return Console(highlight=False, soft_wrap=True)


def logo(word: str = "CASEBENCH") -> list[str]:
    return ["".join(GLYPHS[letter][row] for letter in word) for row in range(4)]


def intro(subtitle: str) -> None:
    out = console()
    out.print()
    for row, shade in zip(logo(), SHADES, strict=True):
        out.print(Text(row, style=f"bold {shade}"))
    out.print(Text(f"{TAGLINE} · v{__version__}", style="dim"))
    out.print()
    out.print(Text.assemble(("◆ ", "bold #a78bfa"), (subtitle, "bold")))


def step(title: str) -> None:
    out = console()
    out.print(Text(GUTTER, style="dim"))
    out.print(Text.assemble(("◆ ", "bold #60a5fa"), (title, "bold")))


def line(text: str, style: str = "") -> None:
    console().print(Text.assemble((f"{GUTTER}  ", "dim"), (text, style)))


def ok(text: str) -> None:
    line(f"✓ {text}", "green")


def warn(text: str) -> None:
    line(f"! {text}", "yellow")


def fail(text: str) -> None:
    line(f"✗ {text}", "red")


def rows(pairs: list[tuple[str, str]]) -> None:
    """Label and value, aligned, under the current step."""
    width = max((len(label) for label, _ in pairs), default=0)
    for label, value in pairs:
        console().print(
            Text.assemble((f"{GUTTER}  ", "dim"), (f"{label:<{width}}  ", "bold"), (value, ""))
        )


@contextmanager
def working(text: str) -> Iterator[None]:
    """A spinner on a terminal; one line elsewhere, so a log shows what ran."""
    out = console()
    if out.is_terminal:
        with out.status(Text(text), spinner="dots"):
            yield
    else:
        out.print(Text.assemble(("◇ ", "dim"), (f"{text}…", "")))
        yield


def review(title: str, pairs: list[tuple[str, str]]) -> None:
    """What is about to be written, framed, before the user agrees to it."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    for label, value in pairs:
        table.add_row(label, value)
    out = console()
    out.print(Text(GUTTER, style="dim"))
    out.print(Panel(table, title=title, title_align="left", border_style="#60a5fa", expand=False))


def outro(lines: list[str]) -> None:
    out = console()
    out.print(Text(GUTTER, style="dim"))
    for number, text in enumerate(lines):
        mark = "└ " if number == 0 else "  "
        out.print(Text.assemble((mark, "bold #22d3ee"), (text, "bold" if number == 0 else "")))
    out.print()
