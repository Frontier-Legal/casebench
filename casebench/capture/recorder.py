"""Collect proxied exchanges and decide which case each one belongs to."""

import secrets
import threading

from casebench.capture.step import HttpExchange


def trace_id_of(traceparent: str | None) -> str | None:
    """The trace id in a W3C `traceparent` value, if it is well formed."""
    if not traceparent:
        return None
    parts = traceparent.strip().split("-")
    return parts[1] if len(parts) == 4 and len(parts[1]) == 32 else None


class Recorder:
    """Exchanges by case: by trace context when the agent passes it on, otherwise the only
    case running; with several running and no trace context, an exchange stays unattributed."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trace_to_case: dict[str, str] = {}
        self._active: list[str] = []
        self._exchanges: dict[str, list[HttpExchange]] = {}
        self.unattributed: list[HttpExchange] = []

    def begin(self, case_id: str) -> str:
        """Start a case and return the `traceparent` to send the agent."""
        trace_id, span_id = secrets.token_hex(16), secrets.token_hex(8)
        with self._lock:
            self._trace_to_case[trace_id] = case_id
            self._active.append(case_id)
            self._exchanges[case_id] = []
        return f"00-{trace_id}-{span_id}-01"

    def end(self, case_id: str) -> list[HttpExchange]:
        """Stop a case and hand back its exchanges in the order they started."""
        with self._lock:
            self._active.remove(case_id)
            found = self._exchanges.pop(case_id, [])
        return sorted(found, key=lambda exchange: exchange.started or 0.0)

    def add(self, exchange: HttpExchange, traceparent: str | None) -> None:
        with self._lock:
            case_id = self._trace_to_case.get(trace_id_of(traceparent) or "")
            if case_id is None and len(self._active) == 1:
                case_id = self._active[0]
            if case_id is not None and case_id in self._exchanges:
                self._exchanges[case_id].append(exchange)
            else:
                self.unattributed.append(exchange)
