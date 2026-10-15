---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Three lines connect a Python agent in its own process, an endpoint takes one flag, and a run keeps no content

Amends [0008](0008-zero-code-capture-before-decorators.md) (what `cb.instrument()` is) and [0044](0044-onboarding-by-a-coding-agent.md) (where the follow path runs). Builds the SDK sketched in [integrations.md](../design/integrations.md).

## Context and problem statement

Some teams try a tool from a notebook or a script, not from a config file and a command. For them, connecting an agent should take three lines: import Casebench, turn capture on, run a suite against the agent's function. `integrations.md` sketched `cb.instrument()` as turning on OpenTelemetry instrumentors on a private tracer. Since then, 0044 records a Python agent's calls by sending them through the recording proxy's follow path, in httpx2, httpx and requests. That records the same calls with no instrumentor, and with no tracer to keep apart from the app's own.

A captured step also kept the arguments of each tool call and of each function named in `capture.functions`. Those often hold a client's facts, such as a search for a party's name. The authority funnel needs none of them: it reads document ids (0031).

## Considered options

1. `cb.instrument()` sends the process's calls in httpx2, httpx and requests through the follow path; `cb.run(agent, suite=...)` runs the suite in this process, as `casebench run` does.
2. `cb.instrument()` turns on the OpenTelemetry instrumentors on a private tracer provider, as sketched.
3. No SDK: a script calls `casebench run --python`.

## Decision outcome

Chosen option 1, because the follow path already records what the reports read, for any SDK built on those libraries, and it creates no span, so it cannot reach the app's own exporter. Option 2 needs one instrumentor per library, each with its own content setting and its own releases. Option 3 restarts the agent in a worker, so a notebook's agent, built in memory, cannot be measured.

- **`cb.instrument()`** patches the transports of httpx2, httpx and requests in this process, once. A call goes to its own host unchanged until a run starts. It adds no tracer provider, span processor or exporter, sets no environment variable, and returns the libraries it records.
- **`cb.run(agent, suite=...)`**
  - `agent` is a function, sync or async, or a generator, called with the case's inputs it names, as the Python target calls one. A URL string instead sends each case to that HTTP endpoint.
  - `suite` is a frozen suite's folder.
  - It reads `casebench.yaml` when one is there, for the judges, the corpora, the capture routes and the perimeter (0046). `allow=[...]` adds hosts the agent calls, as `network: allow:` does.
  - It starts the recording proxy in this process and points the patched libraries at it for the length of the run, without setting any variable. The proxy's own calls upstream are never sent back to it. Cases are asked one at a time, so every call belongs to the case running.
  - It writes the run log as `casebench run` does, scores it, prints the summary and the command that opens it in the workbench, and returns the run's folder.
  - `await cb.arun(...)` does the same inside a running event loop, such as a notebook's.
- **An HTTP service in any language.** `casebench run --endpoint URL` sends each case as `{"question": ...}` by POST and reads `answer` from the JSON reply; the judge reads the citations from the answer's text. An endpoint with another shape gets a `target:` block in `casebench.yaml`.
- **No content is kept.** Before a result is stored, the arguments of each tool call and of each named function are dropped from its steps. What is kept is ids, names, models, token counts, sizes and times. A model's messages were never kept. `capture: {content: true}` keeps the arguments, for a team that wants to read them.
- **Conformance.** Each library the follow path patches has a test at the version the lockfile installs: a chat completion sent through it, in the agent's own process, is recorded with its model and its tokens.

### Consequences

- Good, because three lines measure an agent built in memory, with the same capture, scoring and report as a command.
- Good, because a stored run holds no client facts beyond the answer, which scoring needs.
- Bad, because a run in the agent's own process runs one case at a time.
- Bad, because a team that read tool arguments in its runs now sets `content: true` to keep them.

## Revisit when

- A common agent stack sends its calls through a client the follow path does not patch.
- Teams ask for cases in parallel in one process.

## More information

- [integrations.md](../design/integrations.md), [instrumentation.md](../design/instrumentation.md)
