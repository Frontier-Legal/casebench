# Casebench harness evaluation

## Summary

- Verdict on "evaluate the effect of each harness step": supported, narrower than first stated. Score the outcome and use the trace to explain it. No source supports grading the path as the headline score.
- With a court or hybrid reference Casebench knows the gold authorities, so it can follow each one through the harness (retrieved → kept → read → cited → characterised correctly) with no LLM judging blame.
- Asking a judge "which step failed" is unreliable (14.2% step accuracy on Who&When). Attribution comes from deterministic stage metrics plus counterfactual runs (oracle context, one swapped stage).
- Trace intake is optional. A plain black-box target still gets a full outcome report; a target that sends a trace also gets diagnostics.

## What the field does (checked 2026-09-29)

| Source | Position | Casebench takes |
|---|---|---|
| [Anthropic, Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | "grade what the agent produced, not the path it took"; checking tool-call order is "too rigid"; read transcripts; layer evals | outcome is the score; transcripts shown beside failures |
| [OpenAI trace grading](https://developers.openai.com/api/docs/guides/trace-grading) | grade the whole trace to find where the agent did well or badly, beside black-box evals | trace as diagnosis, not score |
| [LangChain agentevals](https://github.com/langchain-ai/agentevals) | trajectory match (strict, unordered, subset, superset); strict only when order is a compliance rule | path checks only as opt-in assertions |
| [DeepEval component evals](https://deepeval.com/docs/evaluation-component-level-llm-evals), [Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/) | metrics per span: retriever vs generator (context precision/recall, faithfulness, tool-call F1) | stage metrics, computed against legal gold data |
| [promptfoo tracing](https://www.promptfoo.dev/docs/tracing/) | ingests OTLP; assertions on spans and `trajectory:*` | OTLP intake |
| [RAGChecker](https://arxiv.org/abs/2408.08067) | claim-level metrics split into retriever (claim recall, context precision) and generator (context utilisation, noise sensitivity, hallucination, faithfulness) | the retriever/generator split |
| [Who&When](https://arxiv.org/abs/2505.00212) | best method finds the failing agent 53.5% and the failing step 14.2% of the time | no judge-based blame |
| [AgenTracer](https://arxiv.org/abs/2509.03312), [Causal Agent Replay](https://arxiv.org/abs/2606.08275) (preprint) | counterfactual replay and fault injection attribute failures better than judges | the ablation mode |
| [Stanford RegLab](https://arxiv.org/html/2405.20362) | legal answers graded for correctness and groundedness (grounded, misgrounded, ungrounded); causes include naive retrieval, inapplicable authority, reasoning error | the error labels below |
| [Harvey BigLaw Bench](https://www.harvey.ai/blog/introducing-biglaw-bench) | separate Answer score and Source score | answer and authority reported apart |
| [LegalBench-RAG](https://arxiv.org/abs/2408.10343), [CLERC](https://arxiv.org/abs/2406.17186) | legal retrieval evaluated on its own; CLERC: best generator also hallucinates most | retrieval diagnostics are worth their own view |

## Three layers, never blended

| Layer | Question | Needs | Counts toward the headline |
|---|---|---|---|
| 1. Outcome | is the output right, per task metric? | output only | yes |
| 2. Stage diagnostics | where did the right authority drop out, or the wrong one come in? | a trace with document ids | no, shown beside failures and as funnels |
| 3. Counterfactual runs | does fixing one stage fix the outcome? | a target that accepts a stage override | no, a separate experiment report |

Opt-in path assertions ("must consult the statute in force", "must not cite an unverified source") are scored as their own named metrics, never folded into layer 1.

## The authority funnel (layer 2)

For every gold authority in a case's reference (a statute article or a decision the court relied on, or one a lawyer listed):

| Step | Deterministic check | Failure label |
|---|---|---|
| Retrieved | its document id appears in any retrieval span | `retrieval_miss` |
| Kept | it survives rerank or filtering | `rerank_drop` |
| Read | it is in the context of the generating model call | `not_in_context` |
| Cited | the output cites it | `ignored_authority` |
| Characterised | the cited passage supports the claim (reference-anchored judge) | `misgrounded` |

For every citation in the output that is not gold:

| Check | Label |
|---|---|
| never appeared in any retrieval or tool result | `ungrounded` (written from model memory) |
| retrieved, resolves in the corpus, but does not support the claim | `misgrounded` |
| resolves, supports the claim, and is valid law on the date | `extra_valid` (not an error; shown so the gold set can grow) |
| does not resolve in the corpus | `fabricated` |

The report shows the funnel per suite (how many gold authorities survive each step) and per case. That turns "the answer was wrong" into "the right decision was retrieved in 81% of cases but reached the model's context in 52%": a rerank or context-budget problem, not a model problem.

## Counterfactual runs (layer 3)

| Experiment | What changes | Reads as |
|---|---|---|
| Oracle context | the generator gets the gold authorities instead of retrieved ones | outcome gain = ceiling lost to retrieval |
| Stage swap | one stage is replaced (another reranker, prompt or model) | paired per-case difference with a confidence interval |
| Stored re-score | new scorers run over old logs, nothing is re-run | cheap reanalysis (the Inspect `inspect score` pattern) |

Experiments need the target to expose a hook: a Python target with named stages, or an HTTP target that accepts a `casebench_override` field. Casebench never patches a harness it cannot see.

## Trace contract

Casebench accepts, in order of preference:

1. Its own zero-code capture ([integrations.md](integrations.md)): SDK instrumentors, the recording proxy in front of model and backend calls, and config-named functions.
2. OTLP spans in the [OTel GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai) (still "Development" status in Sep 2026), Casebench's internal model ([decision 0003](../decisions/0003-opentelemetry-genai-trace-model.md)). Casebench also maps [OpenInference](https://arize-ai.github.io/openinference/spec/semantic_conventions.html) spans for teams already using them. OpenInference code is being donated to OpenTelemetry, and its RERANKER kind is the reference for the `casebench.rerank.*` extension ([instrumentation.md](instrumentation.md)).
3. A `trace` array in the target's response, the plain JSON fallback below.
4. Import from Langfuse or LangSmith by run id (R2; both accept OTel and OpenInference today).

```json
{"answer": "...", "citations": [{"ref": "Yargıtay 9. HD E.2023/1 K.2024/2", "doc_id": "tr-...-2024-2"}],
 "trace": [
  {"id": "s1", "parent": null, "kind": "retrieval", "query": "...", "docs": [{"id": "tr-...", "score": 0.82}]},
  {"id": "s2", "parent": null, "kind": "rerank", "in": ["tr-...", "..."], "out": ["tr-..."]},
  {"id": "s3", "parent": null, "kind": "llm", "model": "...", "context_doc_ids": ["tr-..."], "tokens": 5120},
  {"id": "s4", "parent": null, "kind": "tool", "name": "statute_lookup", "args": {}, "result_doc_ids": ["..."]}]}
```

Minimum useful trace: stage kind, ranked document ids per retrieval, ids in and out of rerank, the ids in the generating call's context, and each output citation mapped to a document id. Message text stays optional, so a harness can send ids without sending content. Without document ids no stage diagnostic is possible, and the report says so.

## What this does not do

- It never scores a harness lower for taking a different valid path.
- It never asks an LLM which step "caused" a failure.
- Traces stay in the run log on the user's machine. They reach the cloud or team server only when the engineer pushes with `--traces`, as ids and numbers, never message content ([workbench.md](workbench.md)).
