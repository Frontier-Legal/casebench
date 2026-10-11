---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# A function named in the config is wrapped when the agent's process starts

## Context and problem statement

Some steps never leave the agent's process: a rerank in plain Python, a filter over search results, a fallback that calls a job queue. The recording proxy ([0019](0019-recording-proxy.md)) cannot see them, yet the authority funnel needs the document ids going in and out. Zero-code capture ([0008](0008-zero-code-capture-before-decorators.md)) means the team names the function instead of decorating it.

## Considered options

- The config names the function and where its ids are; each worker wraps it before importing the agent
- A `@step` decorator in the agent's code
- Python's `sys.setprofile` tracing every call

## Decision outcome

Chosen option: "the config names the function", because the agent's code stays as it ships.

```yaml
capture:
  functions:
    - function: search/rerank.py:rerank      # or package.module:Class.method
      step: rerank
      doc_ids_in: "$.arguments.candidates[*].id"
      doc_ids_out: "$.result[*].id"
```

- Each worker process ([0020](0020-python-process-wrapper.md)) imports the named function's module and replaces the function with a wrapper before it imports the agent, so later `from module import function` lines get the wrapper, and calls inside the same module find it by name.
- The wrapper calls the original unchanged, then records one step with its kind, its duration and the ids found by two JSONPath expressions over `{"arguments": ..., "result": ...}`: `arguments` holds the call's arguments by parameter name, `result` the return value. Dataclasses, pydantic models and plain objects are read as their fields.
- A step whose expressions find no ids carries the note "no diagnostic possible".
- Async functions get an async wrapper. A name that cannot be found stops the run before the first case, with the name in the error.

### Consequences

- Good, because a rerank inside a search tool shows its ids in and out with one config entry.
- Bad, because a module that bound the function before the wrapper was installed keeps the original; the worker installs wrappers first to make that rare.
- Bad, because arguments and results pass through the JSONPath reader; very large ones cost time per call.

## Revisit when

Agents commonly bind functions in ways the wrapper misses, or the per-call cost of reading ids shows in a measurement.

## More information

- [jsonpath-ng](https://github.com/jsonpath-ng/jsonpath-ng)
- [`inspect.Signature.bind`](https://docs.python.org/3/library/inspect.html#inspect.Signature.bind)
