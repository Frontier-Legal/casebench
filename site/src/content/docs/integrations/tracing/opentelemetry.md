---
title: OpenTelemetry
description: The OTLP spans Casebench accepts, every GenAI and OpenInference attribute it reads, and how spans join their case.
kind: reference
sidebar:
  order: 1
---

Casebench receives OTLP/HTTP trace exports at `POST /v1/traces` on its capture server, in protobuf or JSON, and turns spans into steps. The receiver listens whenever the capture server runs. `capture.traces: true` sets `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` for the agents Casebench starts. See [Send OpenTelemetry spans](/developers/guides/capture/opentelemetry-spans/).

## Attributes read

Casebench reads two sets of attribute names: the OpenTelemetry GenAI semantic conventions and OpenInference. A span may use either.

### Kind of step

| Attribute | Value | Step |
| --- | --- | --- |
| `gen_ai.operation.name` | `chat`, `text_completion`, `generate_content` | model call |
| `gen_ai.operation.name` | `execute_tool` | tool call |
| `gen_ai.operation.name` | `retrieval` | retrieval |
| `gen_ai.operation.name` | `rerank` | rerank |
| `openinference.span.kind` | `LLM`, `TOOL`, `RETRIEVER`, `RERANKER` | the same four |
| `casebench.rerank.output_ids` | present | rerank |

### Details

| Read | From |
| --- | --- |
| Step name | `gen_ai.tool.name`, `tool.name`, else the span name |
| Provider | `gen_ai.provider.name`, `gen_ai.system`, `llm.provider` |
| Model | `gen_ai.response.model`, `gen_ai.request.model`, `llm.model_name` |
| Input tokens | `gen_ai.usage.input_tokens`, `llm.token_count.prompt` |
| Output tokens | `gen_ai.usage.output_tokens`, `llm.token_count.completion` |
| Retrieved ids | `gen_ai.retrieval.documents[*].id` (a list, or JSON text), else `retrieval.documents.N.document.id` |
| Rerank ids in | `casebench.rerank.input_ids`, else `reranker.input_documents.N.document.id` |
| Rerank ids out | `casebench.rerank.output_ids`, else `reranker.output_documents.N.document.id` |

`casebench.rerank.input_ids` and `casebench.rerank.output_ids` are Casebench's own extension for a rerank that neither convention covers.

## Joining spans to cases

A span belongs to the case whose W3C trace id it carries. Casebench sends each case's trace context as the `traceparent` header to an HTTP target and as `TRACEPARENT` to a command. A Python worker makes it the current OpenTelemetry context while the agent answers, when the agent has OpenTelemetry installed. Without a known trace id, a span belongs to the only case running, and is kept as unattributed when several run.

## No double counting

When the proxy recorded a model call that started within a model-call span, the span is dropped and the proxy's record is kept.

## Related

- [Capture server API: `POST /v1/traces`](/developers/reference/capture-api/).
