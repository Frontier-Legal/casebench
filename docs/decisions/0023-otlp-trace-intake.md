---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Traces a team already emits are received over OTLP and joined to cases

## Context and problem statement

Some harnesses already export OpenTelemetry spans, with the GenAI conventions or OpenInference's. Their retrieval and rerank spans can carry the document ids the authority funnel needs, often for steps the recording proxy cannot see. Casebench should accept those spans as they are and tie each one to the case that caused it ([0003](0003-opentelemetry-genai-trace-model.md)).

## Considered options

- An OTLP/HTTP receiver at `/v1/traces` on the Casebench process, protobuf and JSON, mapped by a small normaliser
- An OpenTelemetry Collector the user runs, exporting to a file Casebench reads
- Importing from Langfuse or LangSmith after the run

## Decision outcome

Chosen option: "an OTLP/HTTP receiver in the Casebench process", because a team points its exporter at one URL and nothing else runs.

- `POST http://127.0.0.1:<port>/v1/traces` accepts `application/x-protobuf` (decoded with the official `opentelemetry-proto` messages) and `application/json` (OTLP/JSON, whose trace and span ids are hex).
- A span belongs to the case whose trace context it carries. Casebench sends each case's `traceparent` to the agent ([0019](0019-recording-proxy.md)); a Python worker ([0020](0020-python-process-wrapper.md)) also makes it the current OpenTelemetry context when the agent has OpenTelemetry installed, so spans the agent starts join the case's trace. Without a known trace id, a span belongs to the only case running, as exchanges do.
- Mapping, read on 2026-10-11 from the GenAI conventions (all "development") and OpenInference:
  - `gen_ai.operation.name` `chat`, `text_completion` or `generate_content`, or `openinference.span.kind` `LLM`: a model call with provider, model and tokens.
  - `execute_tool` or `TOOL`: a tool call with `gen_ai.tool.name` or `tool.name`.
  - `retrieval` with `gen_ai.retrieval.documents[*].id`, or `RETRIEVER` with `retrieval.documents.N.document.id`: a retrieval step.
  - `RERANKER` with `reranker.input_documents.N.document.id` and `reranker.output_documents.N.document.id`, or `casebench.rerank.input_ids` and `casebench.rerank.output_ids`: a rerank step.
  - A retrieval or rerank span without ids carries the note "no diagnostic possible". Other spans are ignored.
- When the proxy and a span both saw one model call, the proxy's step stays and the span's is dropped, so a call is never counted twice.
- Casebench sets `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` for the agents it starts only when `capture.traces: true`, so a team's own trace export is never redirected unasked. `casebench proxy env` prints the line.

### Consequences

- Good, because LangChain, LlamaIndex and Haystack retrievers instrumented by either convention give their document ids with no Casebench code in the agent.
- Bad, because the conventions are still changing; the attribute names above are pinned here and in a test, and a rename is a change to this record.

## Revisit when

The GenAI conventions reach stable status or rename an attribute above, or define a rerank span.

## More information

- [OTLP specification](https://opentelemetry.io/docs/specs/otlp/)
- [GenAI spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md)
- [OpenInference semantic conventions](https://arize-ai.github.io/openinference/spec/semantic_conventions.html)
