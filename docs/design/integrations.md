# Casebench integrations: any stack in 3 lines

## Summary

- Goal: a team connects its existing agent loop to Casebench in 3 lines, whatever it uses (OpenAI, Anthropic, Gemini, LangChain, LangGraph, LlamaIndex, OpenRouter, Fireworks, LiteLLM, raw HTTP, custom Python).
- `cb.instrument()` turns on existing OpenTelemetry instrumentors for whatever libraries are installed, on a private tracer provider. `cb.run(target, suite=...)` calls the team's own function or endpoint and scores it.
- Zero code is the default, in three tiers chosen from a list at `casebench init` ([decision 0008](../decisions/0008-zero-code-capture-before-decorators.md)). Model calls go through SDK instrumentors (Python) or the recording proxy (any language): provider, model, latency, tokens, tool calls paired from the stream. Any HTTP backend the agent calls (vector store, reranker, document API) goes through the same proxy, with one line of config naming the JSONPath where its response holds document ids; no parser is written per vendor. In-process steps (Python) are named in the config, and Casebench wraps them at process start. `@cb.step` remains for teams that prefer code. Any agent, the maintainers' own included, is onboarded this way, with no Casebench code inside it.
- Which instrumentors: official OpenTelemetry GenAI packages first, OpenInference only where OTel has no package yet, our own code only for rerank and custom retrieval. Everything is normalised to OTel GenAI semconv, so the source is swappable ([instrumentation.md](instrumentation.md)).
- We write no provider monkeypatches of our own. MLflow keeps a patch module per integration (`safe_patch` on SDK internals); a small project cannot keep up with that churn.
- OpenAI-compatible providers (OpenRouter, Fireworks, Together, vLLM, Groq) need nothing extra. They go through the OpenAI SDK, so the OpenAI instrumentor traces any `base_url`.
- Casebench never touches the app's global tracer provider unless asked. DeepEval does at import ([issue #2497](https://github.com/confident-ai/deepeval/issues/2497)); MLflow and Langfuse isolate by default, and so do we.

## The 3-line quickstarts

```python
# Any Python agent function (OpenAI, Anthropic, Gemini, LiteLLM, OpenRouter, Fireworks inside)
import casebench as cb

cb.instrument()  # auto-detects installed SDKs and frameworks
cb.run(my_agent, suite="tr-labour-sample")  # my_agent(question: str) -> str | dict
```

```python
# LangChain / LangGraph
import casebench as cb

cb.instrument("langchain")
cb.run(lambda question: graph.invoke({"messages": [("user", question)]}), suite="tr-labour-sample")
```

```python
# A deployed HTTP service, any language
import casebench as cb

agent = cb.http("https://agent.firm.internal/ask", body={"q": "{question}"}, answer="$.answer")
cb.run(agent, suite="tr-labour-sample")
```

```bash
# The same without Python code
casebench run --endpoint https://agent.firm.internal/ask --suite tr-labour-sample
```

`cb.run` returns a result object, writes the run log, and prints a link to the workbench (`casebench ui`). `suite` accepts a bundled sample name, a path, or a list of cases built in Python.

## The target contract

| The team's function returns | Casebench does |
|---|---|
| `str` | keeps the text; the judge lists its citations when it grades |
| `dict` with `answer`, optional `citations`, `documents` | uses the returned citations and document ids directly |
| anything, with spans captured by `cb.instrument()` | reads retrieval, rerank, tool and LLM spans for the authority funnel ([harness-eval.md](harness-eval.md)) |

- Case inputs are passed as keyword arguments by name (`question`, `facts`, `document`, `instruction`), the MLflow `predict_fn` convention, so an existing function usually fits unchanged.
- Retrieval spans carry document ids (OTel `gen_ai.retrieval.documents`, OpenInference `document.id`). `cb.run(..., doc_id="metadata.decision_id")` maps the team's ids to corpus ids when they differ. With that one argument, the authority funnel works on LangChain and LlamaIndex retrievers without other changes.
- Async functions and generators are supported; `cb.run(..., max_concurrency=8)` sets concurrency.
- In `casebench.yaml` a target is `python` (`entry: module:function`, called per case inside the wrapped process), `http` (`url`, `body`, `answer`, and an optional `start` command the wrapper runs and waits on) or `command` (`run` with `{question}`; stdout is the answer). `openai_compatible` and `mcp` are presets on `http`.

## Stack coverage

| Stack | Captured by | Extra |
|---|---|---|
| Any Python agent, no edit to its code | `casebench run --python agent.py`: the process starts under OTel zero-code auto-instrumentation with the registry's instrumentors, the `opentelemetry-instrument` mechanism | none |
| OpenAI SDK, incl. OpenRouter, Fireworks, Together, vLLM, Groq via `base_url` | instrumentor per library, chosen in [instrumentation.md](instrumentation.md) | `casebench[openai]` |
| Anthropic, Google GenAI, Bedrock, LiteLLM | same | `casebench[anthropic]`, `[gemini]`, `[bedrock]`, `[litellm]` |
| LangChain, LangGraph, LlamaIndex, DSPy | same | `casebench[langchain]`, `[llamaindex]`, `[dspy]` |
| OpenAI Agents SDK, smolagents, Agno | same | matching extra |
| Already traced with OTel, Langfuse, MLflow or Phoenix | Casebench accepts OTLP; spans joined to cases by W3C `traceparent` | none |
| HTTP service in any language | `cb.http` or `--endpoint`; optional OTLP export to Casebench's local receiver | none |
| Any language, any SDK, no tracing | `cb.proxy()` or `casebench proxy`: point `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` at a local recording proxy (the [Inspect bridge](https://inspect.aisi.org.uk/agent-bridge.html) pattern); every model call with model, latency, tokens and the tool calls it asked for; for streams the proxy requests the usage event and reads it at the end; no retrieval spans | none |
| Vector store, reranker, document API over HTTP | the recording proxy in front of the backend (its base URL variable points at `casebench proxy`); a JSONPath route in the config names where the response holds document ids | none |
| In-process step, such as a rerank in plain Python | the function named in `casebench.yaml` with its argument and return mapping, wrapped at process start; Python only | none |
| Rerankers, custom retrieval, custom steps | `@cb.step("rerank")` or `with cb.span("retrieve", docs=ids):` | none |

Extras are named after the user's library, never after the instrumentation vendor, so a source can change without a breaking change. `casebench[all]` installs everything. The core depends only on the OTel API and SDK.

## Design rules

| Rule | Why |
|---|---|
| Private `TracerProvider` with an in-memory processor; opt-in `cb.instrument(attach_global=True)` | never hijack or duplicate the app's own telemetry |
| Spans tied to a case through a context variable set by `cb.run` | concurrent cases never mix traces |
| Tool calls are paired from the model stream: the tool call the model asked for and the tool result in the next request give name, arguments, result size, and the gap between them as execution time | per-tool numbers with no decorator |
| Time no span accounts for is shown as a gap ("3.2 s between model call 4 and 5"); naming it costs one line in the config, or one `cb.span` | the limit of zero-code capture: in-process logic is invisible from outside |
| Instrumentors are third-party, pinned by extra, enabled only after passing our recorded-fixture conformance tests; ours are only `@cb.step`, `cb.span`, the proxy and the OTLP receiver | coverage without owning per-SDK patches |
| If a library is already instrumented by the app (instrumentors are singletons), attach a span processor to the app's provider instead, and say so | otherwise capture silently yields nothing |
| Message content capture is off by default; Casebench needs document ids, not text | client privilege; OTel defaults off, OpenInference and OpenLLMetry default on |
| When two layers trace the same model call (LangChain over OpenAI), the outermost span wins | no double-counted calls or tokens |
| `cb.score(run_or_traces, scorers=...)` re-scores stored runs or imported traces without calling the agent | the MLflow `evaluate(data=traces)` pattern; cheap reanalysis |
| Nothing is sent anywhere except the target and the judge the user configured | same privacy rule as [open-source.md](open-source.md) |

## What we take from MLflow, and what we leave

MLflow 3.16.1 (Apache-2.0) is the closest reference for "evaluate a GenAI app in the team's own code" ([GenAI docs](https://mlflow.org/docs/latest/genai/)).

| MLflow does | Casebench |
|---|---|
| `mlflow.<flavor>.autolog()` across about 90 integrations ([list](https://mlflow.org/docs/latest/genai/tracing/integrations/)) | one `cb.instrument()`, same coverage idea, built on official OTel instrumentors instead of our own patches |
| `mlflow.genai.evaluate(data, predict_fn, scorers)`; rows are `{"inputs", "expectations"}`; inputs passed as kwargs ([quickstart](https://mlflow.org/docs/latest/genai/eval-monitor/quickstart/)) | `cb.run(target, suite, scorers)`; same kwargs convention; references are evidenced facts and criteria, not free-text expectations |
| Evaluate existing traces without re-running (`search_traces` → `evaluate`) | `cb.score` over run logs and imported traces |
| Built-in judges (Correctness, RetrievalGroundedness, Guidelines, ToolCallCorrectness) and `make_judge` | legal metrics (citation integrity, outcome, statute, criteria) plus custom `@cb.metric`; judges always get the case's evidence |
| Isolated tracer provider by default | copied |
| OTLP in and out | copied |
| Needs a tracking server and experiments; full package is about 45 dependencies and ~1 GB; eval needs the full package ([lightweight SDK](https://mlflow.org/docs/latest/genai/tracing/lightweight-sdk/)) | no tracking server; one local process (`casebench ui`) on a SQLite file; small core with optional extras |
| First evaluation in the quickstart is about 50 lines | first evaluation in 3 lines against a bundled sample suite |

Teams already on MLflow keep it: Casebench accepts their traces over OTLP and can write scores back as `gen_ai.evaluation.result` events.
