---
title: Agents in other languages
description: Test an agent written in TypeScript, Go, Java or anything else, through an HTTP endpoint or a command, with its model calls recorded through routes.
sidebar:
  order: 4
---

Casebench is a Python tool, and your agent does not have to be. It reaches an agent in any language through two targets:

| The agent | Target | Guide |
| --- | --- | --- |
| Serves an HTTP endpoint | `http`, with an optional `start` command | [Connect an HTTP agent](/developers/guides/connect/http-agent/) |
| Is a script or a command-line tool | `command` | [Connect a command](/developers/guides/connect/command-agent/) |

## Model calls go through routes

Casebench follows calls to their host only inside a Python worker. An agent in another language reaches the recording proxy through routes: variables that point its clients at the proxy. The proxy works over HTTP, so the language that made the call does not matter.

- If your SDK reads its base URL from `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` or `GOOGLE_GEMINI_BASE_URL`, as the official TypeScript SDKs for OpenAI and Anthropic read theirs, Casebench records each call with no change. The proxy forwards it to the address the variable held before, or to the provider's default host.
- If your code reads the base URL from a variable of its own, add a route that points that variable at the proxy. See [Record model calls](/developers/guides/capture/model-calls/#command-and-http-targets-use-routes).
- A base URL written into the code cannot be routed without a code change. Such a call is neither recorded nor held to the [perimeter](/developers/guides/setup/network/).

For an agent that is already running, name `capture.port` and set the lines `casebench proxy env` prints in the agent's environment.

## What `init` reads

`casebench init` reads `package.json` as well as Python dependency files, and names the model SDKs it finds there. It reads code for client construction in Python only, so for an agent in another language it offers no route. Write routes for your own variables by hand.

## Keep calls with their case

With more than one case at a time, pass the `traceparent` header Casebench sends on to your outgoing calls, or read `TRACEPARENT` in a command. Most OpenTelemetry setups do this already. Without it, run one case at a time.

## Related

- [An agent in TypeScript](/examples/walkthroughs/typescript-agent/), end to end.
- [Send OpenTelemetry spans](/developers/guides/capture/opentelemetry-spans/), for steps the proxy cannot see.
