---
title: Connect an HTTP agent
description: Reach an agent that already serves an HTTP endpoint, in any language, with a JSON body template, JSONPath for the answer, and its model calls recorded through routes.
sidebar:
  order: 2
---

Use an HTTP target when your agent already serves an endpoint, whatever language it is written in. Casebench sends one request per case and reads the answer out of the JSON response.

Do not put the login of the app built on your agent in front of it. Casebench should reach the agent the way your own code does. If the endpoint is only reachable inside your network, [set up here and run there](/developers/guides/runs/run-elsewhere/).

## Describe the request and the response

```yaml title="casebench.yaml"
target:
  type: http
  url: http://127.0.0.1:8000/ask
  method: POST                              # the default
  headers:
    Authorization: Bearer ${AGENT_TOKEN}    # read from the shell or a file under keys:
  body:
    query: "{{question}}"
    options: { jurisdiction: GB, max_sources: 8 }
  answer: $.answer                          # JSONPath into the response
  citations: $.sources[*].citation          # optional
  documents: $.sources[*].id                # optional
  timeout_s: 120                            # optional; no timeout unless you set one
  max_concurrency: 4
```

`casebench init --target http --url URL` asks for the body and the answer's JSONPath, and writes this block. The target's host is one the run may call, so it needs no entry under `network: allow:`.

### Placeholders in the body

- A string that is exactly `{{name}}` is replaced by the case input with its JSON type. `"{{question}}"` becomes the question as a JSON string.
- Inside a longer string, `{{name}}` is replaced as text: `"Answer as a lawyer: {{question}}"`.
- An input name the case does not have is an error before anything is sent.

### Headers

A header's `${NAME}` is read at request time from the shell, or from the `.env` file `keys:` names for it. Casebench treats the variable as a key: its value never appears in a run's files. See [Keep keys out of the config](/developers/guides/setup/keys/).

### Reading the response

`answer` must find the answer text. A response with a status of 400 or above fails that case. `citations` and `documents` are optional, and Casebench stores what they find with the result. Without `citations`, the judge lists the citations from the answer text when it grades.

## Let Casebench start the service

Give a `start` command and Casebench runs it before the first case, waits until the endpoint answers, and stops it when the run ends:

```yaml title="casebench.yaml"
target:
  type: http
  url: http://127.0.0.1:8000/ask
  start: uv run uvicorn app:api --port 8000
  body: { query: "{{question}}" }
  answer: $.answer
```

The wait has no deadline of its own. It ends when the endpoint answers anything, when the start command exits, with an error naming its exit code, or when you stop the run.

The service starts with Casebench's environment, plus the variables that point its model clients at the recording proxy. Keys Casebench read from `.env` files are not in it, so the service loads its own settings as it does in production.

## Record its model calls

Casebench cannot reach inside another process, so an HTTP agent's calls are recorded through routes: variables that point the agent's clients at the proxy. For a service Casebench starts, it sets them itself. For one that is already running, name a port and print the variables:

```yaml title="casebench.yaml"
capture:
  port: 8790
```

```sh
casebench proxy env
```

```text frame="terminal"
ANTHROPIC_BASE_URL=http://127.0.0.1:8790/anthropic
GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:8790/gemini
OPENAI_BASE_URL=http://127.0.0.1:8790/openai/v1
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:8790/v1/traces
```

Set them where the agent runs, not in the shell that runs Casebench. A route forwards to the address its variable holds in Casebench's own environment, so pointing that one at the proxy too sends the proxy's calls back to itself. `casebench init` writes `port: 7463` for an HTTP target when it writes a route, and prints the same lines. [Record model calls](/developers/guides/capture/model-calls/#command-and-http-targets-use-routes) has the details.

## Keep calls attributed when cases run in parallel

Casebench sends a W3C `traceparent` header with every request. Pass it on to your model and backend calls, as most OpenTelemetry setups do, and each recorded call is attributed to its case even with `max_concurrency` above 1. Without it, calls are attributed only while one case runs at a time. The rest are attributed to no case, and no report counts them.

## No timeout by default

How long an answer takes is part of what you measure. Casebench does not cut a slow answer off unless you set `timeout_s`.

## Check it

```sh
casebench target check
```

It sends "Hi. How are you?" and shows the parsed answer, the citations and the steps it recorded. Pass `--question` to ask something else:

```sh
casebench target check --question "Can a fixed-term contract be renewed indefinitely?"
```

## Related

- [Connect a command](/developers/guides/connect/command-agent/) for scripts and command-line tools.
- [Agents in other languages](/integrations/sdks/other-languages/).
- [An agent in TypeScript](/examples/walkthroughs/typescript-agent/), end to end.
