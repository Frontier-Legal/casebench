# Casebench instrumentation sources

## Summary

- Normalise on the OpenTelemetry GenAI semantic conventions (`gen_ai.*`), the vendor-neutral CNCF standard ([decision 0003](../decisions/0003-opentelemetry-genai-trace-model.md)). Add a small `casebench.rerank.*` extension until upstream defines rerank.
- Prefer the official OTel GenAI instrumentors (`opentelemetry-instrumentation-genai-*`, Apache-2.0, multi-vendor, Beta 1.2b0 on 2026-09-24).
- OpenInference is a per-library fallback, not the foundation. Arize donated its code to OpenTelemetry, and the SIG is merging it package by package.
- Every source sits behind one normaliser and a conformance test, so swapping one is a registry change, not a user-facing change.
- Zero-code first ([decision 0008](../decisions/0008-zero-code-capture-before-decorators.md)). The process wrapper (`opentelemetry-instrument` mechanism), the recording proxy and OTLP intake ship at R1. `@cb.step` and `cb.span` are for in-process steps only ([integrations.md](integrations.md)).

## What changed the picture (checked 2026-09-29)

| Fact | Source |
|---|---|
| Arize proposed donating OpenInference instrumentation code to OpenTelemetry (proposal marked done); the holding repo was archived 2026-06-16 and the GenAI SIG "cherry-picks instrumentations one by one" | [community#3467](https://github.com/open-telemetry/community/issues/3467), [donation-openinference](https://github.com/open-telemetry/donation-openinference) |
| The OpenInference spec was not adopted; "OpenTelemetry will continue to use its own GenAI semantic conventions" | [community#3467](https://github.com/open-telemetry/community/issues/3467) |
| Official GenAI instrumentors moved to [opentelemetry-python-genai](https://github.com/open-telemetry/opentelemetry-python-genai): openai, anthropic, bedrock, langchain, llama-index, openai-agents, google-genai, dspy, smolagents, agno and more, at Beta 1.2b0; contributors from Microsoft, Google, Snowflake, Elastic, SolarWinds | [PyPI](https://pypi.org/pypi/opentelemetry-instrumentation-genai-openai/json) |
| The SIG prefers native first-party instrumentation and retires its own when that aligns | [CONTRIBUTING](https://github.com/open-telemetry/opentelemetry-python-genai/blob/main/CONTRIBUTING.md) |
| GenAI semconv lives in [semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai); all attributes still "development"; retrieval span yes, rerank span no | repo |
| Dynatrace agreed to acquire Arize, the main contributor to OpenInference, announced 2026-08-13; not confirmed closed | [Dynatrace](https://ir.dynatrace.com/news-events/press-releases/detail/435/dynatrace-to-acquire-ai-observability-leader-arize) |
| ServiceNow acquired Traceloop (OpenLLMetry) in March 2026; "OpenLLMetry will remain open-source" | [Traceloop](https://traceloop.com/blog/traceloop-is-joining-servicenow) |

## Options compared

| Source | Licence | Governance | Coverage for us | Emits | Caveat |
|---|---|---|---|---|---|
| Official OTel GenAI (`opentelemetry-instrumentation-genai-*`) | Apache-2.0 | CNCF, multi-vendor | openai, anthropic, google-genai, bedrock, langchain, llama-index, openai-agents; no LiteLLM | `gen_ai.*` | Beta; some packages first released days ago; content capture via a process-wide env var |
| OpenInference | Apache-2.0 | Arize (an estimated 50 to 65% of commits), Dynatrace once its acquisition closes | about 40 instrumentors incl. LiteLLM, RERANKER span kind | own schema; opt-in `gen_ai.*` dual-write since May 2026 | content capture on by default |
| OpenLLMetry | Apache-2.0 | ServiceNow | wide, incl. LiteLLM | mostly `gen_ai.*` plus own attributes | publishes under un-namespaced `opentelemetry-instrumentation-*` names that collide with official ones; content on by default |
| Pydantic Logfire | MIT | Pydantic | openai, anthropic native; others delegated to OTel or OpenInference | `gen_ai.*` | heavier dependencies |
| MLflow tracing | Apache-2.0 | LF AI & Data, Databricks-led | about 90 autologs | MLflow span schema | pulls `databricks-sdk`; usage telemetry on by default |
| Own wrappers | ours | ours | whatever we write | ours | re-implements streaming, async and tool parsing per SDK version |

## Per-library pick

| Library | Pick now | Fallback | Switch when |
|---|---|---|---|
| openai (+ OpenRouter, Fireworks via `base_url`) | `opentelemetry-instrumentation-genai-openai` | OpenInference openai | |
| anthropic | `opentelemetry-instrumentation-genai-anthropic` | OpenInference anthropic | |
| google-genai | `opentelemetry-instrumentation-google-genai` | OpenInference google-genai | |
| bedrock | `opentelemetry-instrumentation-botocore` (Bedrock extension) | `…-genai-bedrock` | the genai package passes our fixtures; never enable both |
| litellm | OpenInference litellm with `gen_ai.*` dual-write on | LiteLLM's native OTel callback | an official OTel package ships |
| langchain / langgraph | `opentelemetry-instrumentation-genai-langchain` (has retriever spans) | OpenInference langchain | fixtures decide which is default at R1 |
| llama-index | OpenInference llama-index | `…-genai-llama-index` | the official package stabilises (first release 2026-09-24) |
| openai-agents | `opentelemetry-instrumentation-genai-openai-agents` | OpenInference openai-agents | |
| rerankers, custom retrieval | Casebench `@cb.step` / `cb.span` with `casebench.rerank.*` | OpenInference RERANKER as the reference shape | OTel semconv defines rerank |
| httpx, requests, aiohttp, psycopg (vector stores, rerankers, SQL, labelled by host) | the matching `opentelemetry-instrumentation-*` contrib package | | |

## Rules that make the source swappable

| Rule | Why |
|---|---|
| One normaliser maps `gen_ai.*`, OpenInference and OpenLLMetry attributes into Casebench's step model | Langfuse and Braintrust already do this; the user never sees which source was used |
| A registry `library → [candidate instrumentors]` in priority order; the first installed one that passes conformance wins | swapping is a one-line registry change |
| Recorded-fixture conformance tests per library (a real SDK call recorded once, replayed in CI) | Beta packages change; we catch breakage before users do |
| Pin the semconv version Casebench reads; upgrade deliberately | all GenAI attributes are still "development" |
| Instrumentors are singletons: if the app already instrumented a library, attach a span processor to its provider | otherwise capture silently yields nothing |
| Content capture off by default; only ids and metadata are needed | the defaults differ by source, and legal data is privileged |
| Outermost span wins when two layers trace one model call | no double counting |

## Why not the alternatives

- OpenInference as the foundation. Its code is moving into OpenTelemetry anyway, its schema is not the standard OTel chose, and its steward is changing owner. Using it where OTel has a gap costs nothing extra behind the normaliser.
- MLflow as a dependency. A heavier install, a Databricks SDK dependency, telemetry on by default, and its own span schema.
- Our own wrappers everywhere. The maintenance cost MLflow and Inspect carry, with no neutrality benefit over OTel.
