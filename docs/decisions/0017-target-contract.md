---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# A target is a Python entry point, an HTTP endpoint or a command

Amended by [0020](0020-python-process-wrapper.md): python agents run in worker processes, not in the runner's own.

## Context and problem statement

Every score depends on how a case reaches the AI under test and how its answer comes back. Agents are Python functions, HTTP services in any language, or scripts. A team should connect its agent without changing it, and captured steps must stay with the case that caused them when cases run concurrently.

## Considered options

- Three shapes declared in the config (`python`, `http`, `command`), each a built-in target plugin, behind one async contract
- An SDK the agent imports and calls back into
- HTTP only, with Python agents wrapped in a server

## Decision outcome

Chosen option: "three shapes behind one async contract", because it covers a function, a service and a script with no change to the agent.

- **`python`**: `entry: module:function` is imported in the runner's own process and called once per case with the case inputs as keyword arguments, by name. A function that does not take `**kwargs` receives only the inputs it names. Async functions, generators and async generators work; a generator's text chunks are joined. It may return a string or a mapping with `answer`, optional `citations` and `documents`.
- **`http`**: `url`, `body` (a JSON template), `answer` and optional `citations` (JSONPath expressions), optional `headers` with `${VAR}` read from the environment, and an optional `start` command. Casebench starts `start`, waits until the endpoint answers, and stops it when the run ends.
- **`command`**: `run` is split into arguments like a shell would, without a shell, and each `{name}` is replaced by the case input. Standard output is the answer. A non-zero exit is that case's error, not the run's.
- **Placeholders.** In a body template a string that is exactly `{{name}}` becomes the input's value with its JSON type; inside a longer string it is replaced by text. An unknown name is an error before anything is sent.
- **Answers.** A plain-text answer has its citations parsed by the corpus's jurisdiction adapter when one is configured.
- **Concurrency.** Cases run as asyncio tasks, at most `max_concurrency` at once (default 1, one case at a time, so a run never loads an agent harder than the user asked). Each case runs inside its own context variable, so steps captured during it are recorded against it, never against a neighbour.

Budgets, with their reasons:

- **No per-case timeout unless the config sets one.** How long an answer takes is part of what is measured; cutting it at a limit Casebench chose would score a slow answer as a failure.
- **The readiness wait has no deadline of its own.** It ends when the endpoint answers, when the start command exits (an error naming its exit code), or when the user stops the run.
- **Readiness polls every 0.1 s.** A start that completes between two polls is seen at most 0.1 s late, which is small beside any agent call, and the poll is a single local connection.

### Consequences

- Good, because a Python agent, a TypeScript service and a shell script are all measured without edits.
- Good, because the capture tiers can attribute steps through the case context without knowing the target type.
- Bad, because a Python entry point runs in the runner's process, so a crash in the agent ends the run; resuming picks up after the last stored result.

## Revisit when

A common agent shape fits none of the three (a websocket chat, say), or users ask for a default timeout with a measured basis.

## More information

- [Python `contextvars`](https://docs.python.org/3/library/contextvars.html): asyncio copies the context into each task and into `asyncio.to_thread`.
- [RFC 9535, JSONPath](https://www.rfc-editor.org/rfc/rfc9535)
