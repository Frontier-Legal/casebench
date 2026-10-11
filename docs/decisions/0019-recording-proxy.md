---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# A recording proxy captures model and backend calls from any language

## Context and problem statement

Model calls, tool calls and backend calls are where an agent finds or loses the right authority. Agents are written in any language, and teams will not add a tracing library to be measured ([0008](0008-zero-code-capture-before-decorators.md)). Every mainstream model SDK and most vector-store and reranker clients take a base URL from the environment, so a local proxy in front of them sees every call without any change to the agent.

## Considered options

- A reverse proxy inside the Casebench process, one route per upstream, on Starlette and uvicorn
- A forward HTTPS proxy (`HTTPS_PROXY`) with a local certificate authority
- SDK instrumentors only, Python only
- aiohttp for the server and client

## Decision outcome

Chosen option: "a reverse proxy on Starlette and uvicorn", because base-URL variables need no certificate the user must trust, and Starlette is the base of FastAPI, which the workbench will use.

- **Routes.** Each route has a name, an upstream base URL, a parser and the environment variable that points a client at it, such as `anthropic` → `https://api.anthropic.com`, `ANTHROPIC_BASE_URL`. A client calls `http://127.0.0.1:<port>/<route>/...`; the proxy forwards to the upstream and streams the response back as it arrives.
- **Port.** When Casebench starts the agent (a python entry point, a start command or a command target) the operating system picks a free port and Casebench sets the variables itself. For an agent that is already running, the config names a port and `casebench proxy env` prints the lines to set.
- **What is recorded.** Method, URL, request body, status, response body (or the parsed events of a streamed response) and the start and end time. Authorization headers and API keys are never recorded.
- **Usage in streams.** For OpenAI-compatible streams the proxy adds `stream_options.include_usage` when the client did not ask, so a streamed response still reports its tokens. It changes no answer.
- **Which case an exchange belongs to.** Casebench gives each case a W3C trace context and sends it to the agent (a `traceparent` header for HTTP targets, the `TRACEPARENT` variable for commands). An exchange carrying a known trace id belongs to that case. Without one, it belongs to the only case running; with several running and no trace context, it is kept as unattributed and the report says so.
- **Parsers.** Casebench ships parsers for model APIs only (Anthropic, OpenAI, Gemini). A search or rerank backend is read through a JSONPath route: the config names where its response holds document ids, and no parser is written per vendor. How long a search or rerank takes is not measured; only the ids matter to the funnel. Anyone may still publish a parser plugin for a backend.
- **Steps.** A parser turns each exchange into steps. Tool calls are paired across calls: the tool call the model asked for in one response and its result in the next request give the tool's name, arguments, result size and duration. Time between steps that nothing accounts for is reported as a gap.

### Consequences

- Good, because a TypeScript, Go or Python agent is captured the same way, and the parsers are plugins anyone can add.
- Good, because the proxy runs in the Casebench process, so nothing listens after a run ends.
- Bad, because a client that ignores base-URL variables is not captured; the report shows no steps for it rather than guessing.
- Bad, because several concurrent cases need the agent to pass the trace context on; otherwise run them one at a time.

## Revisit when

A widely used SDK stops honouring base-URL variables, or agents commonly need concurrency without propagating trace context.

## More information

- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [OpenTelemetry environment variables as context carriers](https://opentelemetry.io/docs/specs/otel/context/env-carriers/)
- [OpenAI streaming usage](https://platform.openai.com/docs/api-reference/chat/create#chat-create-stream_options)
- [Starlette](https://www.starlette.io/), [uvicorn](https://www.uvicorn.org/)
