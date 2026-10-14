"""Print one line per case answered and per case scored, when a run writes to a log (0038)."""

import threading
from collections.abc import Callable

from casebench.runs.log import Result


class Progress:
    """Counts what is done of `total`; cases are scored on several threads at once."""

    def __init__(self, total: int, echo: Callable[[str], None]) -> None:
        self.total = total
        self.echo = echo
        self.answered = 0
        self.scored = 0
        self.lock = threading.Lock()

    def answered_one(self, result: Result) -> None:
        with self.lock:
            self.answered += 1
            seconds = (result.latency_ms or 0) / 1000
            what = "failed" if result.error else "answered"
            self.echo(f"{what} {self.answered}/{self.total} {result.case_id} in {seconds:.1f}s")

    def scored_one(self, case_id: str, seconds: float, cost: float | None) -> None:
        with self.lock:
            self.scored += 1
            spent = "cost unknown without a price" if cost is None else f"${cost:.2f} so far"
            self.echo(
                f"scored {self.scored}/{self.total} {case_id} in {seconds:.1f}s, judge {spent}"
            )
