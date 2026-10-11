---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Python agents run in worker processes, one per parallel slot

Amends [0017](0017-target-contract.md): the python target no longer runs the agent in the runner's own process.

## Context and problem statement

The recording proxy ([0019](0019-recording-proxy.md)) captures a Python agent's model and backend calls once its SDKs' base URLs point at the proxy. With several cases running at once, every call must be tied to the case that caused it. Tagging calls with trace context depends on instrumenting the HTTP library each SDK uses, and in 2026 the Anthropic and OpenAI SDKs moved from httpx to httpx2, which no published OpenTelemetry instrumentation covers. Casebench writes no SDK patches of its own ([0008](0008-zero-code-capture-before-decorators.md)).

## Considered options

- One worker process per parallel slot, each with its own proxy path, each answering one case at a time
- One case at a time whenever capture is on
- Trace context injected by HTTP-library instrumentations

## Decision outcome

Chosen option: "one worker process per parallel slot", because a call's proxy path then says which worker made it, and a worker answers one case at a time, so attribution is exact whatever HTTP library the agent uses.

- `casebench run --python agent.py` runs the suite against `agent.py`'s `answer` function; `--python agent.py:respond` names another. It is the python target of [0017](0017-target-contract.md) with its entry given on the command line.
- With `max_concurrency` N, Casebench starts N workers. Each imports the agent once, with every base-URL variable pointing at the proxy under its own prefix, `http://127.0.0.1:<port>/w/<worker>/<route>`.
- A worker reads one case, calls the entry, and writes back the answer and any steps recorded in its process. Messages are length-prefixed JSON over the worker's standard input and output, so they have no size limit; the agent's own prints go to standard error.
- A worker that dies fails its case with the exit code and is replaced; the run goes on.
- The OpenTelemetry HTTP instrumentations are not used.

### Consequences

- Good, because attribution needs nothing from the agent or its HTTP library.
- Good, because a crash in the agent costs one case, not the run.
- Bad, because N workers import the agent N times, so start-up and memory grow with concurrency.
- Bad, because an agent that keeps state between calls in memory sees only the cases its own worker answered.

## Revisit when

Starting workers costs more than the cases they run, or an agent needs shared in-memory state across cases.

## More information

- [httpx2](https://github.com/pydantic/httpx2)
- [Python `asyncio` subprocesses](https://docs.python.org/3/library/asyncio-subprocess.html)
