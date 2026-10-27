---
title: Record model calls
description: See every model call your agent makes, with model, tokens, latency and tool calls. A Python agent's calls are followed to where they go; a command or HTTP agent's go through routes.
sidebar:
  order: 1
---

During `casebench run`, `casebench check` and `casebench target check`, Casebench starts a recording proxy on `127.0.0.1`. Each call your agent makes passes through it to the real API, the reply streams back as it arrives, and Casebench records the call against the case that caused it. You change no code.

How a call reaches the proxy depends on the target:

| Target | How its calls reach the proxy | Config needed |
| --- | --- | --- |
| Python | The worker sends each call through the proxy's follow path, to the host the agent's code chose | None |
| Command, or HTTP with `start` | Routes: variables such as `OPENAI_BASE_URL` that Casebench points at the proxy | None for the built-in routes; a route for a variable of your own |
| HTTP, already running | The same routes, with variables you set where the agent runs | `capture.port`, and the lines from `casebench proxy env` |

## What is recorded

For each call: the method, the URL, the request body, the status, the response body or the events of a streamed response, and the start and end time. From those, a parser reads the provider, the model, input and output tokens, and the tool calls the model asked for.

Request headers are never recorded, so neither are keys. In the URL, the value of a query parameter whose name contains `key`, `token`, `secret`, `signature` or `password` becomes `REDACTED`.

Tool calls are paired across calls: the tool call the model asked for in one response and its result in the next request give the tool's name, arguments, result size and how long it ran. Time between steps that nothing accounts for shows as a gap, such as `gap between retrieval Qdrant search and llm claude-sonnet-4-5`.

## A Python agent's calls are followed

Each worker that runs a Python target rewrites every call made through httpx2, httpx or requests to the proxy's follow path:

```text
http://127.0.0.1:<port>/w/<worker>/~/<scheme>/<host>/<path>
```

A call to `https://api.anthropic.com/v1/messages` from worker 0 goes to `http://127.0.0.1:<port>/w/0/~/https/api.anthropic.com/v1/messages`. The proxy forwards it to `https://api.anthropic.com/v1/messages` unchanged and records it against the case worker 0 is answering.

- The call goes where the agent's code and settings send it. Casebench leaves `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` and `GOOGLE_GEMINI_BASE_URL` in the worker as your project set them, so a key reaches only the host the project chose.
- A client built with a literal base URL, such as `OpenAI(base_url="https://llm.firm.internal/v1")`, is followed too.
- `casebench init` writes no capture route for a Python target, and says so: "each model and search call is recorded where it goes; no route is needed".
- The openai 3.x and anthropic 1.x SDKs send through httpx2. Earlier SDKs and many agents' own clients send through httpx. A call through another library, such as aiohttp or gRPC, still goes where the agent sends it, but it is not recorded and the [perimeter](/developers/guides/setup/network/) does not see it.
- Production never loads the worker, so it never runs this rewrite.

The proxy reads a followed call in this order:

1. A route at the call's host. The built-in routes sit at `api.openai.com`, `api.anthropic.com` and `generativelanguage.googleapis.com`. A route under `capture.routes`, or one Casebench adds for an HTTP corpus, sits at its `upstream`.
2. Otherwise, each parser in turn. A parser reads only its own API's paths, such as `/chat/completions` for `openai`, so the first one that returns a step is the one whose API the call is. Nothing is chosen by the host's name. A call to OpenRouter through the OpenAI SDK is read this way.
3. Otherwise, the search APIs Casebench knows, by their paths. See [Record retrieval steps](/developers/guides/capture/retrieval-steps/).

A call none of these reads is still forwarded, but it adds no step.

## Command and HTTP targets use routes

A command or an HTTP agent runs in its own process, which Casebench cannot hook. Its calls reach the proxy through variables. Each built-in parser declares a route:

| Route | Variable | Default upstream |
| --- | --- | --- |
| `openai` | `OPENAI_BASE_URL` | `https://api.openai.com`, with `/v1` |
| `anthropic` | `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` |
| `gemini` | `GOOGLE_GEMINI_BASE_URL` | `https://generativelanguage.googleapis.com` |

For a command target or an HTTP target with `start`, Casebench picks a free port and sets each variable to `http://127.0.0.1:<port>/<route>` plus its suffix. A route forwards to the address its variable held before Casebench changed it, in your shell or in a file under `keys:`. Only when the variable held nothing does it forward to the default upstream. So with `OPENAI_BASE_URL=https://openrouter.ai/api/v1` in your shell, the `openai` route forwards to `https://openrouter.ai/api/v1`.

If your code reads its base URL from a variable of its own, add a route for it:

```yaml title="casebench.yaml"
capture:
  routes:
    - name: llm-gateway
      upstream: https://llm.firm.internal
      parser: openai
      env: LLM_GATEWAY_URL
      env_suffix: /v1
```

`casebench init` finds these by reading your Python code as text, for a command or HTTP target, and offers a route named after the full host, such as `api-fireworks-ai` for `api.fireworks.ai`. A route's `upstream` is a host the run may call, so it needs no entry under `network: allow:`.

A client whose base URL is a literal in the code cannot be routed for a command or HTTP target without a code change. `init` names the place.

A route you write under `capture.routes` keeps its variable pointed at the proxy in a Python worker too. Python agents rarely need one.

## When the agent is already running

Name a port, so the address stays the same:

```yaml title="casebench.yaml"
capture:
  port: 8790
```

Print the lines to set in the agent's environment:

```sh
casebench proxy env
```

```text frame="terminal"
ANTHROPIC_BASE_URL=http://127.0.0.1:8790/anthropic
GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:8790/gemini
OPENAI_BASE_URL=http://127.0.0.1:8790/openai/v1
LLM_GATEWAY_URL=http://127.0.0.1:8790/llm-gateway/v1
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:8790/v1/traces
```

Start the agent with those variables set, then run the suite. The proxy listens for as long as the command runs. Without `capture.port`, `casebench proxy env` stops and says to set it.

Set the variables in the agent's environment only. If the shell that runs Casebench has `OPENAI_BASE_URL` pointing at the proxy, the `openai` route forwards to the proxy itself.

## Streams report tokens through a route

For a streaming chat completion that does not ask for usage, the proxy adds `stream_options.include_usage`, so the stream still reports its tokens. It does so for a route's calls and for a Python agent's calls alike, and changes nothing else.

A Python agent's followed calls are forwarded exactly as sent. A streamed Chat Completions call that does not ask for usage is recorded without token counts.

## Calls made while several cases run

A Python worker answers one case at a time, and its calls arrive on its own path, so each call is attributed to its case exactly.

For other targets, each case gets a W3C trace context. A call that carries a known trace id belongs to its case. Otherwise it belongs to the only case running. With several cases running and no trace context, it is attributed to no case, and no report counts it, so run one case at a time or pass the trace context on.

## A host the config does not name

The proxy refuses a call to a host `casebench.yaml` does not name. It answers the agent with `403` and the reason, and the run stops. See [Allow the hosts your agent calls](/developers/guides/setup/network/).

## Turn it off

```sh
casebench run --suite suites/employment --no-capture
```

With capture off, a Python worker sends its calls straight to their hosts. Nothing is recorded, and the perimeter does not see the agent's calls.

## Related

- [Record retrieval steps](/developers/guides/capture/retrieval-steps/) for searches, reranks and document fetches.
- [How capture works](/developers/concepts/capture/).
- [Capture server API](/developers/reference/capture-api/) for the proxy's routes.
