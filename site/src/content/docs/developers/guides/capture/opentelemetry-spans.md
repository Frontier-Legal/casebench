---
title: Send OpenTelemetry spans
description: Point an agent that already emits OpenTelemetry spans at Casebench's OTLP receiver, so model, tool, retrieval and rerank spans become steps joined to their case.
sidebar:
  order: 3
---

If your agent is already instrumented with OpenTelemetry, send its spans to Casebench during a run. Spans in the GenAI semantic conventions or in OpenInference become steps, joined to their case by trace context. Use this for steps the proxy cannot see, such as a search over gRPC or a rerank inside another service.

## Turn the receiver on

The recording proxy accepts OTLP/HTTP at `POST /v1/traces`, in protobuf and in JSON, for as long as it runs. To have Casebench point an agent it starts at the receiver, set:

```yaml title="casebench.yaml"
capture:
  traces: true
```

For a Python target, a command target or an HTTP target with `start`, Casebench then sets `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` to its receiver. It never redirects your trace export unless you ask.

For an agent that is already running, name a `port` and copy the line from `casebench proxy env`, which prints it whatever `traces` says:

```text frame="terminal"
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:8790/v1/traces
```

A Python worker sends the export to the proxy's own address, so the follow path leaves it alone.

## Join spans to cases

A span belongs to the case whose trace id it carries. Casebench sends each case's `traceparent` to the agent: as a header for HTTP targets and as the `TRACEPARENT` variable for commands. A Python worker also makes it the current OpenTelemetry context when the agent has OpenTelemetry installed, so spans the agent starts join the case's trace with no code. A span with no known trace id belongs to the only case running, and is kept as unattributed when several run.

## What becomes a step

| Span | Step |
| --- | --- |
| `gen_ai.operation.name` `chat`, `text_completion` or `generate_content`, or `openinference.span.kind` `LLM` | A model call, with provider, model and tokens |
| `execute_tool`, or `TOOL` | A tool call named by `gen_ai.tool.name` or `tool.name` |
| `retrieval` with `gen_ai.retrieval.documents[*].id`, or `RETRIEVER` with `retrieval.documents.N.document.id` | A retrieval |
| `rerank` or `RERANKER` with input and output document ids, or `casebench.rerank.input_ids` and `casebench.rerank.output_ids` | A rerank |

Other spans are ignored. A retrieval or rerank span without ids carries the note "no diagnostic possible".

When the proxy recorded a model call that started within a model-call span, the proxy's record is kept and the span is dropped, so no call is counted twice.

## Message content stays optional

Casebench needs document ids, not text. Leave content capture off in your instrumentation. The funnel works without it.

## Related

- [OpenTelemetry](/integrations/tracing/opentelemetry/): every attribute Casebench reads.
- [`POST /v1/traces`](/developers/reference/capture-api/) in the capture server reference.
