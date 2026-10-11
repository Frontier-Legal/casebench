# Casebench architecture

## Summary

- The unit is an evaluation case, not a court decision. A case is a task the AI performs, a reference to grade against, and the metrics to apply. Court decisions are one way to build references; lawyers are another ([decision 0002](../decisions/0002-evaluation-case-model.md)).
- Three independent axes: task type × reference source × metric. Any combination is legal; the report never mixes them into one number.
- A reference has two layers: facts, each tied to evidence (a court passage, a lawyer's note, a corpus id), and criteria derived from those facts. No criterion exists without the evidence it came from, so an LLM never invents the rubric it then grades against.
- Everything outside the core is a plugin (task types, reference builders, targets, metrics, corpus connectors, capture parsers, model providers, exporters), found through Python entry points, each kind with a conformance command and a scaffold. A corpus connector says where decisions come from and serves any jurisdiction. There is no per-country code: models extract, and the corpus resolves citations ([decision 0024](../decisions/0024-no-jurisdiction-adapters.md)).
- Teams connect in 3 lines through `cb.instrument()` and `cb.run()` ([integrations.md](integrations.md)); trace capture sources are chosen in [instrumentation.md](instrumentation.md).
- Harness diagnostics and counterfactual runs are in [harness-eval.md](harness-eval.md); court extraction and integrity controls in [design.md](design.md).

## Core concepts

| Concept | Is | Owned by |
|---|---|---|
| Case | one task input + its reference + metric list + tags + provenance + approval state (draft, approved) | suite file |
| Task type | what the AI is asked to do and what its output looks like | plugin (`casebench.tasks`) |
| Reference | facts with evidence pointers, plus criteria derived from them | reference builder plugin |
| Reference source | `court` (extracted from a decision), `lawyer` (authored), `structured` (expected fields), `hybrid` (lawyer answer + corpus-verified authorities) | recorded on every fact |
| Target | the AI under test, reached through a provider; returns an output and optionally a trace | plugin (`casebench.targets`) |
| Metric | scores one aspect of one output; deterministic, judge-based or trace-based; declares its scope (case, step, suite), inputs and direction; inputs bound by key, JSONPath or callable | plugin (`casebench.metrics`) |
| Score | the one record every metric, judge and human review emits: name, kind (code, llm, human), direction, value, label, explanation with quoted evidence, metric version | core |
| Annotation | a lawyer's verdict on a case or score in the viewer, with a reason; an overruled judge verdict becomes calibration data | run log |
| Corpus | read-only store of authorities (decisions, statutes) used for citation checks and court references | plugin (`casebench.corpus`) |
| Suite | a frozen set of cases with a manifest (id, content hash, versions, source mix) | `suite.jsonl` + `manifest.json` |
| Run log | every output, trace, score, cost and error of one suite × target run; re-scorable without re-running | `runs/<run_id>/` |

## Task types

| Task | Input | Output | Typical metrics |
|---|---|---|---|
| `qa` | question, optional facts and documents | answer + citations | conclusion match, citation integrity, criteria pass rate, unsupported claims |
| `outcome` | facts with the operative part removed | ruling label | exact match vs court |
| `research` | research question with date and court constraints | ranked authorities + synthesis | recall@k and nDCG vs gold authorities, missed key authority, citation integrity |
| `drafting` | instruction + facts + optional documents | a document | weighted criteria (required arguments, authority, omissions), citation integrity |
| `editing` | a document + instruction | edited document or annotations | issues found vs reference list, false positives, meaning preserved outside the edit, introduced errors |
| `extraction` | a document + field schema | structured fields | per-field exact or normalised match |
| `citation_check` | an answer with citations | verdict per citation | agreement with Casebench's own resolution |

A task type is a small declarative spec (input schema, output parser, default metrics), in the spirit of [lm-eval-harness task YAML](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/new_task_guide.md) and [Inspect's Task = Dataset + Solver + Scorer](https://inspect.aisi.org.uk/scorers.html).

## Case examples

```yaml
id: tr-labour-0042
task: {type: qa, question: "İşverenin bu nedenle yaptığı fesih geçerli midir?", facts: "..."}
reference:
  source: court
  facts:
    - {kind: outcome, value: invalid_termination, evidence: {doc: tr-yargitay-9hd-2024-1234, span: [8120, 8410]}}
    - {kind: statute, value: "4857/18", evidence: {doc: tr-yargitay-9hd-2024-1234, span: [5020, 5090]}}
  criteria:
    - {id: c1, text: "Concludes the termination is invalid", from: [outcome], weight: 5}
    - {id: c2, text: "Relies on İş Kanunu m. 18", from: [statute], weight: 3}
metrics: [criteria, citation_integrity, unsupported_claims]
```

```yaml
id: firm-contracts-0007
task: {type: editing, instruction: "Flag clauses that create unusual liability.", document: docs/nda-17.docx}
reference:
  source: lawyer
  author: {role: senior associate, id: anon-3}
  facts:
    - {kind: issue, value: "Uncapped indemnity in clause 9.2", evidence: {doc: docs/nda-17.docx, anchor: "9.2"}}
  criteria:
    - {id: c1, text: "Flags clause 9.2 as uncapped", from: [0], weight: 5}
    - {id: c2, text: "Does not change clause 4", from: [], weight: -3, kind: preservation}
metrics: [criteria, edit_preservation, false_positive_issues]
```

Criteria use per-criterion pass/fail with signed integer weights, the scheme [PRBench](https://arxiv.org/html/2511.11562) and BigLaw Bench use (score = Σ weight·pass / Σ positive weights, clipped to 0 to 1). PRBench measured judge-expert κ 0.603 against expert-expert κ 0.589 with this form.

## Components

```
 reference builders ──> suite (frozen) ──> runner ──> target (+ trace) ──> run log ──> metrics ──> report / viewer / exporters
  court (corpus + extractors)   │                                            ▲              │
  lawyer import (csv/yaml/docx) │                                            └── re-score ──┘
  structured, hybrid            └── manifest: hash, versions, source mix
```

| Component | Rule |
|---|---|
| Reference builders | write facts with evidence; derive criteria only from facts; record the extraction models and their agreement |
| Runner | async with per-target rate limits; persists each result before the next; resumable; `--repeats n`; `--dry-run` cost estimate |
| Metrics | receive (case, output, trace, corpus); return a score, a label set and an explanation; never call the target |
| Judge | one provider interface, user's own key; always given the case's evidence, never asked to judge from memory |
| Report | a table per task × metric with n, confidence interval and baseline; filterable by reference source and tag; no overall score |
| Workbench | `casebench ui`: the lawyer-facing web app for golden data, answer review, judge overrule, run compare and reports; local or team server ([workbench.md](workbench.md)) |
| Exporters | Langfuse, LangSmith and Inspect logs; OTel `gen_ai.evaluation.result` events back into the user's traces |

## Package and plugin layout

| Module | Holds |
|---|---|
| `casebench.core` | pydantic models for case, reference, output, trace, score; JSON Schema export for editor autocomplete |
| `casebench.tasks` | built-in task types |
| `casebench.references` | court, lawyer, structured and hybrid builders |
| `casebench.targets` | python callable, http, openai_compatible, mcp, proxy, offline, echo (demo) |
| `casebench.instrument` | `cb.instrument()` over a registry of OTel GenAI instrumentors (OpenInference as fallback) on a private tracer provider; the recording proxy with a parser per model API (plugins in `casebench.capture`) and a JSONPath route for any backend; the semconv normaliser; `@cb.step`, `cb.span`; local OTLP receiver |
| `casebench.providers` | the one provider interface for the judge and the extractors; openai_compatible, anthropic, gemini and bedrock shipped, any other as a plugin |
| `casebench.metrics` | deterministic, judge and trace metrics |
| `casebench.traces` | OTLP intake with OTel GenAI and OpenInference mapping; JSON fallback |
| `casebench.corpus` | folder, S3, SQL, HTTP connectors |
| `casebench.cli` | the commands, including `casebench setup` (an agent prompt that adds the 3 lines to the user's code) |
| `casebench.server`, `casebench.ui` | FastAPI service + bundled React app; SQLite by default, Postgres for teams; the local single-user mode is Apache-2.0, the multi-user layer (roles, SSO, audit, invites, the push/pull server side) lives in `ee/` ([open-source.md](open-source.md)) |
| `casebench.pytest` | `@pytest.mark.casebench(suite=...)`; stable case ids, `git_sha` recorded, exit code is the CI gate |

Third parties publish `casebench-<name>` packages that register entry points in the groups above (the pytest and Inspect plugin model). Framework code never imports a jurisdiction; the registry loads one by the name in the config.

## Boundaries that keep it trustworthy

- Metrics read the corpus; they never ask the target to verify itself.
- Every score row carries the reference source and the approval state. The report never averages court-derived and lawyer-authored results together, nor lawyer-approved and unreviewed cases.
- A run log is append-only. Re-scoring writes a new score set with its own metric versions.
- Casebench is standalone: cases, runs, eval traces and reviews live in its own store (`./.casebench/` locally, Postgres for the team server or the cloud). The runner calls only allowlisted hosts. The shared place receives what `casebench push` sends ([workbench.md](workbench.md)) and never computes a score.
- Human decisions are append-only events and always outrank a judge's verdict.
