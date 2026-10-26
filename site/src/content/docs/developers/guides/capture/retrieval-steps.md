---
title: Record retrieval steps
description: Record which documents each search, rerank and fetch returned, from searches of your corpus and of Qdrant, a backend route, a function named in the config, or OpenTelemetry spans.
sidebar:
  order: 2
---

The [authority funnel](/developers/concepts/authority-funnel/) follows each authority the court relied on through your agent: retrieved, kept, read, cited. It needs one thing from each retrieval step: the ids of the documents it returned. None of the ways below changes your agent's code.

| Your step is | Recorded by | Config needed |
| --- | --- | --- |
| A Python agent's search or fetch of the HTTP corpus Casebench checks against | A route Casebench adds at the corpus's host | None |
| A Python agent's Qdrant search over REST | The known search APIs | None |
| Any other HTTP search engine, vector store, reranker or document API | A backend route | A route under `capture.routes` |
| A Python function, such as an in-process rerank | A function named in the config | An entry under `capture.functions` |
| Already traced with OpenTelemetry | [OTLP spans](/developers/guides/capture/opentelemetry-spans/) | `capture.traces: true` |

The first two work because a Python worker sends every call through the recording proxy to where it goes. See [Record model calls](/developers/guides/capture/model-calls/#a-python-agents-calls-are-followed).

## Searches of your corpus

When your agent searches the same document store Casebench checks citations against, its searches are recorded with no config. For each corpus with the `http` connector, a run adds a route named `corpus-<name>` at the host of the corpus's `base_url`:

- A request whose path matches the corpus's `fetch_path`, such as `/documents/{id}`, is recorded as a fetch of the id in the path.
- Any other request is recorded as a retrieval, with the ids at the corpus's own id path: `search_results` joined with `result_fields.id`, or else `search_ids`.

A `base_url` written as `${NAME}` is read from the shell or a file under `keys:`. No route is added when the variable is set nowhere, or when a route under `capture.routes` already covers that host.

The corpus route reads only calls that reach the proxy by where they go, which is a Python agent's. For a command or HTTP agent, write a backend route with the variable its code reads the store's address from.

## Qdrant searches

A Python agent's call to a Qdrant REST search is recorded as a retrieval with the ids of the points it returned. The proxy matches a `POST` by its path:

- `/collections/{name}/points/search` and `/collections/{name}/points/search/batch`
- `/collections/{name}/points/query` and `/collections/{name}/points/query/batch`

The Qdrant Python client sends REST calls through httpx, which the worker redirects. A client set to gRPC is not recorded.

`casebench init` names the store when your dependency files list `qdrant-client`:

```text frame="terminal"
│  search   Qdrant (qdrant-client), its searches recorded as retrievals
```

A `casebench target check` against an agent that searches Qdrant before its model call shows both steps:

```text frame="terminal"
steps      3 captured
  retrieval Qdrant search (doc-1, doc-2)
  gap between retrieval Qdrant search and llm claude-sonnet-4-5
  llm claude-sonnet-4-5
```

These ids are Qdrant's point ids. When the point keeps the corpus id in a payload field, add a route at the store's host whose `doc_ids` reads that field, as the next section shows. The reply holds the payload only when the agent's request asks for it with `with_payload`.

## A backend over HTTP

Add a route for the backend and say where the response holds document ids. For a command or HTTP agent, also name the variable your code reads the backend's address from. A Python agent needs no `env`: its call reaches the route at the route's host.

```yaml title="casebench.yaml"
capture:
  routes:
    - name: search
      upstream: http://127.0.0.1:9200
      env: SEARCH_URL
      step: retrieval
      doc_ids: $.hits.hits[*]._source.decision_id
    - name: rerank
      upstream: https://rerank.firm.internal
      env: RERANK_URL
      step: rerank
      doc_ids_in: $.documents[*].id
      doc_ids: $.results[*].id
    - name: vectors
      upstream: https://vectors.firm.internal:6333
      doc_ids: $.result.points[*].payload.decision_id
```

- `doc_ids` is a JSONPath into the response. For a rerank, `doc_ids_in` reads the request too, so Casebench knows what went in and what came out.
- `fetch_path`, such as `/documents/{id}`, marks the requests that read one document. They are recorded as a fetch of the id in the path, not as a retrieval.
- `step` is `retrieval` unless you name another.
- A route's `upstream` is a host the run may call, so it needs no entry under `network: allow:`.

For a command or HTTP target, `casebench init` offers a route for a backend whose client reads its base URL from a variable, when that host is a configured `http` corpus, with the corpus's own id paths.

## A function in your Python code

Name the function, and say where its arguments and its return value hold ids:

```yaml title="casebench.yaml"
capture:
  functions:
    - function: search/rerank.py:rerank      # or package.module:Class.method
      step: rerank
      doc_ids_in: $.arguments.candidates[*].id
      doc_ids_out: $.result[*].id
```

Each worker replaces the function with a wrapper before it imports your agent, so later imports get the wrapper. The wrapper calls the original unchanged and records one step. The JSONPath runs over `{"arguments": ..., "result": ...}`, where `arguments` holds the call's arguments by parameter name. Dataclasses, pydantic models and plain objects are read as their fields. `step` is `rerank` unless you name another.

A name that cannot be found stops the run before the first case, with the name in the error. Python targets only.

## When your ids differ from the corpus's

The funnel compares the ids your steps carry with the corpus's ids. Point the JSONPath at the field that holds the corpus id, such as `$.hits.hits[*]._source.decision_id`, rather than at your store's internal id. Casebench writes a corpus id as `<corpus name>:<id>`. A bare id, as the store gives it, still matches when exactly one of the case's authorities and citations ends in it.

## A step that finds no ids

A step whose expressions find nothing carries the note "no diagnostic possible", and the funnel counts only cases with ids. With no ids anywhere, the report says so instead of giving a number:

```text frame="terminal"
authority funnel: no diagnostic possible; no captured step carried document ids
```

## Related

- [The authority funnel](/developers/concepts/authority-funnel/), and how to read it.
- [A retrieval agent with the funnel](/examples/walkthroughs/retrieval-funnel/), end to end.
