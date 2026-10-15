# Casebench integrations: any stack in 3 lines

## Summary

- Goal: a team connects its existing agent loop to Casebench in 3 lines, whatever it uses (OpenAI, Anthropic, Gemini, LangChain, LangGraph, LlamaIndex, OpenRouter, Fireworks, LiteLLM, raw HTTP, custom Python).
- `cb.instrument()` patches httpx2, httpx and requests, the HTTP libraries the common model SDKs send through, so that while `cb.run` runs, each call goes through the recording proxy's follow path to the host the agent chose. It creates no tracer and sets no variable ([decision 0062](../decisions/0062-three-lines.md)). `cb.run(target, suite=...)` calls the team's own function or endpoint and scores it.
- Zero code is the default, in three tiers chosen from a list at `casebench init` ([decision 0008](../decisions/0008-zero-code-capture-before-decorators.md)). Model calls go through SDK instrumentors (Python) or the recording proxy (any language): provider, model, latency, tokens, tool calls paired from the stream. Any HTTP backend the agent calls (vector store, reranker, document API) goes through the same proxy, with one line of config naming the JSONPath where its response holds document ids; no parser is written per vendor. In-process steps (Python) are named in the config, and Casebench wraps them at process start. `@cb.step` remains for teams that prefer code. Any agent, the maintainers' own included, is onboarded this way, with no Casebench code inside it.
- Which instrumentors: official OpenTelemetry GenAI packages first, OpenInference only where OTel has no package yet, our own code only for rerank and custom retrieval. Everything is normalised to OTel GenAI semconv, so the source is swappable ([instrumentation.md](instrumentation.md)).
- We write no patch per provider SDK. A patch module per SDK breaks with every SDK release, and a small project cannot keep up with that churn. The only patch is at the three HTTP libraries, and parsers read each provider's API from the recorded call.
- OpenAI-compatible providers (OpenRouter, Fireworks, Together, vLLM, Groq) need nothing extra. They go through the OpenAI SDK, so the OpenAI instrumentor traces any `base_url`.
- Casebench creates no tracer provider and never touches the app's own.

## The 3-line quickstarts

```python
# Any Python agent function (OpenAI, Anthropic, Gemini, LiteLLM, OpenRouter, Fireworks inside)
import casebench as cb

cb.instrument()  # patches httpx2, httpx and requests, those installed
cb.run(my_agent, suite="suites/tr-labour")  # my_agent(question: str) -> str | dict
```

```python
# LangChain / LangGraph
import casebench as cb

cb.instrument()
cb.run(lambda question: graph.invoke({"messages": [("user", question)]}), suite="suites/tr-labour")
```

```python
# In a notebook, whose event loop is already running
import casebench as cb

cb.instrument()
await cb.arun(my_agent, suite="suites/tr-labour")
```

```python
# A deployed HTTP service, any language: POST {"question": ...}, read "answer"
import casebench as cb

cb.run("https://agent.firm.internal/ask", suite="suites/tr-labour")
```

```bash
# The same without Python code
casebench run --endpoint https://agent.firm.internal/ask --suite suites/tr-labour
```

`cb.run` writes the run log, scores it, prints the command that opens it in the workbench (`casebench ui`), and returns the run's folder. `suite` is a frozen suite's folder. `casebench.yaml`, when there is one, gives the judges, the corpora and the perimeter; `allow=[...]` adds hosts the agent calls. An endpoint with another request or reply shape gets a `target:` block in `casebench.yaml`.

## The target contract

| The team's function returns | Casebench does |
|---|---|
| `str` | keeps the text; the judge lists its citations when it grades |
| `dict` with `answer`, optional `citations`, `documents` | uses the returned citations and document ids directly |
| anything, with its calls recorded through `cb.instrument()` | reads retrieval, rerank, tool and LLM steps for the authority funnel ([harness-eval.md](harness-eval.md)) |

- Case inputs are passed as keyword arguments by name (`question`, `facts`, `document`, `instruction`), so an existing function usually fits unchanged.
- Retrieval steps carry document ids: from a known search API's reply, such as Qdrant's ([decision 0061](../decisions/0061-the-first-ten-minutes.md)), from a route's `doc_ids` JSONPath, or from OTLP spans (OTel `gen_ai.retrieval.documents`, OpenInference `document.id`).
- Async functions and generators are supported. In the agent's own process cases run one at a time, so every call belongs to the case running; `casebench run` runs a Python agent in workers, several at once.
- In `casebench.yaml` a target is `python` (`entry: module:function`, called per case inside the wrapped process), `http` (`url`, `body`, `answer`, and an optional `start` command the wrapper runs and waits on) or `command` (`run` with `{question}`; stdout is the answer). `openai_compatible` and `mcp` are presets on `http`.

## Stack coverage

| Stack | Captured by | Extra |
|---|---|---|
| Any Python agent, no edit to its code | `casebench run --python agent.py`: the process starts under OTel zero-code auto-instrumentation with the registry's instrumentors, the `opentelemetry-instrument` mechanism | Casebench installed in the agent's own environment, as a dev dependency: the agent's function runs in Casebench's Python, so its packages must be there. A command target needs no shared environment. |
| OpenAI SDK, incl. OpenRouter, Fireworks, Together, vLLM, Groq via `base_url` | instrumentor per library, chosen in [instrumentation.md](instrumentation.md) | `casebench[openai]` |
| Anthropic, Google GenAI, Bedrock, LiteLLM | same | `casebench[anthropic]`, `[gemini]`, `[bedrock]`, `[litellm]` |
| LangChain, LangGraph, LlamaIndex, DSPy | same | `casebench[langchain]`, `[llamaindex]`, `[dspy]` |
| OpenAI Agents SDK, smolagents, Agno | same | matching extra |
| Already traced with OpenTelemetry, by any tracing tool | Casebench accepts OTLP; spans joined to cases by W3C `traceparent` | none |
| HTTP service in any language | `cb.http` or `--endpoint`; optional OTLP export to Casebench's local receiver | none |
| Any language, any SDK, no tracing | `cb.proxy()` or `casebench proxy`: point `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` at a local recording proxy; every model call with model, latency, tokens and the tool calls it asked for; for streams the proxy requests the usage event and reads it at the end; no retrieval spans | none |
| Vector store, reranker, document API over HTTP | the recording proxy in front of the backend (its base URL variable points at `casebench proxy`); a JSONPath route in the config names where the response holds document ids | none |
| In-process step, such as a rerank in plain Python | the function named in `casebench.yaml` with its argument and return mapping, wrapped at process start; Python only | none |
| Rerankers, custom retrieval, custom steps | `@cb.step("rerank")` or `with cb.span("retrieve", docs=ids):` | none |

Extras are named after the user's library, never after the instrumentation vendor, so a source can change without a breaking change. `casebench[all]` installs everything. The core depends only on the OTel API and SDK.

## Design rules

| Rule | Why |
|---|---|
| No tracer provider: calls are recorded at the HTTP libraries and the proxy | never hijack or duplicate the app's own telemetry |
| Calls tied to a case by the proxy: by the worker's path, by trace context, or as the only case running | concurrent cases never mix calls |
| Tool calls are paired from the model stream: the tool call the model asked for and the tool result in the next request give name, arguments, result size, and the gap between them as execution time | per-tool numbers with no decorator |
| Time no span accounts for is shown as a gap ("3.2 s between model call 4 and 5"); naming it costs one line in the config, or one `cb.span` | the limit of zero-code capture: in-process logic is invisible from outside |
| Instrumentors are third-party, pinned by extra, enabled only after passing our recorded-fixture conformance tests; ours are only `@cb.step`, `cb.span`, the proxy and the OTLP receiver | coverage without owning per-SDK patches |
| The proxy's own calls upstream are never followed back to it, in the agent's own process | a run cannot loop on itself |
| No content is kept: messages never are, and tool and function arguments are dropped before a result is stored unless `capture: {content: true}` ([decision 0062](../decisions/0062-three-lines.md)); Casebench needs document ids, not text | client privilege |
| When two layers trace the same model call (LangChain over OpenAI), the outermost span wins | no double-counted calls or tokens |
| `cb.score(run_or_traces, scorers=...)` re-scores stored runs or imported traces without calling the agent | cheap reanalysis |
| Nothing is sent anywhere except the target and the judge the user configured | same privacy rule as [open-source.md](open-source.md) |
