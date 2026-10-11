---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# OpenTelemetry GenAI conventions are the trace model

## Context and problem statement

To show where a multi-step system lost the right authority, Casebench needs the steps it took: model calls, tool calls, retrieval and rerank, with the document ids each step saw. Teams already emit traces in several schemas, and the capture libraries change owners and attribute names. Casebench needs one internal model that every capture source maps into.

## Considered options

- OpenTelemetry GenAI semantic conventions (`gen_ai.*`), with a small `casebench.rerank.*` extension
- OpenInference semantic conventions
- A Casebench-only span schema
- A tracing vendor's own span schema

## Decision outcome

Chosen option: "OpenTelemetry GenAI semantic conventions", because they are the vendor-neutral CNCF standard, the official instrumentors emit them, and the OpenInference code is being donated into OpenTelemetry while its schema was not adopted.

The conventions define a retrieval span but no rerank span, so Casebench adds `casebench.rerank.*` attributes shaped after OpenInference's RERANKER kind until upstream defines one. One normaliser maps `gen_ai.*`, OpenInference and OpenLLMetry attributes into the internal step model, so the source a team uses never shows in the report. Casebench pins the conventions version it reads, because every GenAI attribute is still "development" status.

### Consequences

- Good, because a team that already exports OTLP spans can point its exporter at Casebench with no other change.
- Good, because swapping a capture library is a registry change, not a user-facing change.
- Bad, because the conventions are unstable; an upgrade is a deliberate change with recorded fixtures.
- Bad, because rerank needs an extension that may differ from what upstream eventually defines.

## Revisit when

The GenAI conventions reach stable status, upstream defines a rerank span, or a widely used capture source cannot be mapped without loss.

## More information

- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- [OpenInference donation discussion](https://github.com/open-telemetry/community/issues/3467)
- [../design/instrumentation.md](../design/instrumentation.md) has the per-library choice.
