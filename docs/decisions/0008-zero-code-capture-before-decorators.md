---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Zero-code capture before decorators

## Context and problem statement

The authority funnel needs the document ids each step of an agent saw. Teams will not add a tracing library or decorators to their agent loop just to be measured, and a measurement that requires editing the agent measures a different agent. The tool also has to work for agents written in languages other than Python.

## Considered options

- Zero-code capture in three tiers, with decorators as an optional extra
- An SDK with decorators (`@step`, `span`) as the primary path
- Own monkeypatches per provider SDK

## Decision outcome

Chosen option: "Zero-code capture in three tiers", because it measures the agent as it ships and covers any language.

1. Model calls, through the official OpenTelemetry instrumentors in a wrapped Python process, or a local recording proxy for any language. Tool calls are paired from the model stream.
2. Any HTTP backend the agent calls (vector store, reranker, document API), through the same proxy, read by a parser per known backend or a JSONPath given in the config.
3. In-process Python steps, by naming the function in the config; Casebench wraps it when the process starts.

Time no captured step accounts for is shown as a gap. Decorators stay available as sugar over the same capture for teams that prefer code. Casebench writes no provider monkeypatches of its own.

### Consequences

- Good, because onboarding an agent, the maintainers' own included, needs no change to its code.
- Good, because the proxy works for TypeScript, Go or any client that honours a base-URL variable.
- Bad, because in-process logic is invisible unless named in the config, and the report has to say so.
- Bad, because the proxy must parse each backend's wire format and track its changes.

## Revisit when

A capture tier proves unreliable on recorded fixtures for a widely used stack, or the OpenTelemetry conventions cover retrieval and rerank well enough that the proxy parsers become redundant.

## More information

- [OpenTelemetry Python zero-code instrumentation](https://opentelemetry.io/docs/zero-code/python/)
- [Inspect agent bridge](https://inspect.aisi.org.uk/agent-bridge.html), the recording proxy pattern.
- [../design/integrations.md](../design/integrations.md)
