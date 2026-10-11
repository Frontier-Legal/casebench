"""Turn one case's exchanges into steps, pair tool calls and show unaccounted time."""

from collections.abc import Callable

from casebench.capture.read import ids_in
from casebench.capture.step import HttpExchange, Step, StepKind, ToolCall

ParseExchange = Callable[[HttpExchange], list[Step]]


def paired_tools(steps: list[Step]) -> list[Step]:
    """A tool call asked for in one model response and answered in a later request is a tool
    step: its name and arguments, the result's size, and the time between the two calls."""
    pending: dict[str, tuple[ToolCall, float | None]] = {}
    tools: list[Step] = []
    for step in sorted((s for s in steps if s.kind is StepKind.LLM), key=_start):
        for result in step.tool_results:
            asked = pending.pop(result.id, None)
            if asked is None:
                continue
            call, asked_at = asked
            duration = _ms(asked_at, step.started)
            tools.append(
                Step(
                    kind=StepKind.TOOL,
                    name=call.name,
                    arguments=call.arguments,
                    result_size=result.size,
                    started=asked_at,
                    ended=step.started,
                    duration_ms=duration,
                )
            )
        for call in step.requested_tools:
            pending[call.id] = (call, step.ended)
    return tools


def gaps(steps: list[Step]) -> list[Step]:
    """Time between steps that no step covers, named after the steps on either side.
    Gaps are reported to the millisecond, the resolution durations are shown in."""
    timed = sorted((s for s in steps if s.started is not None and s.ended is not None), key=_start)
    found: list[Step] = []
    covered_until: float | None = None
    before: Step | None = None
    for step in timed:
        assert step.started is not None and step.ended is not None
        if covered_until is not None and before is not None:
            missing = round((step.started - covered_until) * 1000)
            if missing > 0:
                found.append(
                    Step(
                        kind=StepKind.GAP,
                        name=f"between {_label(before)} and {_label(step)}",
                        started=covered_until,
                        ended=step.started,
                        duration_ms=float(missing),
                    )
                )
        if covered_until is None or step.ended > covered_until:
            covered_until, before = step.ended, step
    return found


def assemble(
    exchanges: list[HttpExchange], parse: ParseExchange, in_process: list[Step]
) -> list[Step]:
    parsed = [(exchange, parse(exchange)) for exchange in exchanges]
    known = {i for _, found in parsed for s in found for i in s.doc_ids_out}
    known |= {i for s in in_process for i in s.doc_ids_out}
    steps = [
        step.model_copy(update={"doc_ids_in": ids_in(exchange.request_body, known)})
        if step.kind is StepKind.LLM
        else step
        for exchange, found in parsed
        for step in found
    ] + list(in_process)
    steps += paired_tools(steps)
    steps += gaps(steps)
    return sorted(steps, key=_start)


def _start(step: Step) -> float:
    return step.started if step.started is not None else float("inf")


def _ms(start: float | None, end: float | None) -> float | None:
    return (end - start) * 1000 if start is not None and end is not None else None


def _label(step: Step) -> str:
    return f"{step.kind.value} {step.name or step.model or ''}".rstrip()
