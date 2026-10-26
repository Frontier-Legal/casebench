---
title: How capture works
description: How Casebench records what your agent did on each case, from outside its code, and why a call always goes where your agent sends it.
sidebar:
  order: 7
---

Casebench needs to know what your agent did on each case: which models it called, with how many tokens, which tools it used, which documents each search returned. It learns this from outside the agent, so any agent, including one you do not control, is onboarded the same way.

## Three sources, one model of a step

| Source | Sees | Needs |
| --- | --- | --- |
| The recording proxy | Model calls, searches and other HTTP calls | Nothing for a Python target; a route per service for command and HTTP targets |
| Functions named in the config | In-process Python steps, such as a rerank | A Python target |
| OTLP spans | Whatever your agent already traces | OpenTelemetry in the agent |

Each becomes the same kind of step: a model call, a tool call, a retrieval, a rerank or a document fetch, with its time, tokens and, for retrieval steps, document ids. Time no step accounts for is shown as unaccounted.

## A Python agent: every call, where it goes

A Python target runs in worker processes Casebench starts. Inside a worker, and only there, the HTTP libraries the model SDKs send through (httpx2, httpx and requests) send each call to the local proxy, with the call's own scheme and host in the path. The proxy forwards it to that host unchanged and records it.

So a call always reaches the host your code chose, whatever base URL its settings give, and a key never reaches another host. A client built with a literal base URL is recorded too, with no route. Production never loads the worker, so this never runs there.

Each recorded call is read by the parser for its API: a parser reads only its own API's paths, such as `/v1/messages` or `/chat/completions`, so nothing is decided by the host's name. A search of a configured HTTP corpus is read as a retrieval with the corpus's own id paths, and searches of known search APIs, such as Qdrant's REST API, are read as retrievals too.

## Command and HTTP targets: routes

An agent in its own process cannot be hooked. For it, a route points an environment variable, such as `OPENAI_BASE_URL`, at the proxy, and the proxy forwards to the value that variable already had. `casebench proxy env` prints the variables for an agent that is already running.

## Why not patch the SDKs

Patching each SDK breaks with every SDK release. Sending calls through a local proxy needs no certificate, no code in the agent and no knowledge of an SDK's internals. One parser per model API, not per SDK version, reads the traffic.

## Which case a step belongs to

When several cases run at once, steps must not mix:

- **Python targets** run one case at a time per worker, and each worker's calls carry its own prefix, so each call is attributed exactly.
- **HTTP and command targets** receive the case's W3C trace context, as a `traceparent` header or the `TRACEPARENT` variable. A call or span carrying a known trace id belongs to its case.
- Otherwise a step belongs to the only case running, and with several running it is kept as unattributed. The report says how many.

## What capture does not do

- It does not record request headers, so no API key or authorization header is kept, and URLs are recorded with their credentials removed.
- It does not change requests, except asking OpenAI-compatible streams sent through a route to include usage. A Python agent's followed calls are forwarded exactly as sent, so a stream that does not ask for usage is recorded without tokens.
- It does not let a call leave for a host `casebench.yaml` does not name. See [The perimeter](/developers/concepts/perimeter/).
- It does not touch your app's own tracer provider or redirect your trace export unless `capture.traces` is set.
- It does not score anything. Steps explain scores; they never change one.

## Where you see the steps

Every result's steps are in `results.jsonl`. In the workbench's engineering view, each answer shows them as a waterfall: each model call and tool call a bar with its model, duration, tokens and estimated cost, unaccounted time as its own bar, the authority funnel beside it, and a diff against another run of the same suite.

## The limit of capture from outside

Logic inside one process, such as a filter applied to a list in plain Python, is invisible from outside. It shows as unaccounted time. Naming the function in the config costs one line and makes it a step.

## Related

- [Record model calls](/developers/guides/capture/model-calls/).
- [Record retrieval steps](/developers/guides/capture/retrieval-steps/).
- [Capture server API](/developers/reference/capture-api/).
