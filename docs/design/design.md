# Casebench design: court-derived references

## Summary

- This file covers the court reference source: how a decision becomes reference facts and criteria, and the controls that keep those keys honest.
- The general model (case, task, reference, metric, plugins) is in [architecture.md](architecture.md); harness traces in [harness-eval.md](harness-eval.md).
- The court test types below are task types (`outcome`, `qa`, `research`) with a court reference. Citation integrity runs on every task and every reference source.

```
 corpus connector ──> extractors ──────> generator ──> frozen suite
 (raw decisions)      (two models,      (tests)       (id + hash)
                       answer keys)
                                                                               │
 target connector <────────────────── runner <─────────────────────────────────┘
 (the AI under test)                     │
                                         v
                    scorers: exact · citation · version · reference judge
                                         │
                                         v
                    report (HTML, JSON) · CI gate · exports (Langfuse, LangSmith, Inspect)
```

| Component | Does | Reads | Writes |
|---|---|---|---|
| Corpus connector | lists, samples and fetches decisions by id; resolves a citation to a decision | a folder, S3, a database, or a vendor's document API or MCP | nothing |
| Extractor | two different models read each decision: the ruling as a shared label, the statutes and decisions it relied on as written, and the facts without the ruling | decision records | answer keys plus per-field agreement |
| Generator | builds tests by type, samples and stratifies by court, area and date | answer keys | a suite |
| Suite store | freezes a suite with an id and a content hash | the suite | `suite.jsonl` plus a manifest |
| Target connector | sends a test to the AI under test, parses answer and citations | target config | raw responses |
| Runner | runs tests with concurrency and rate limits, persists each result before the next | suite, target connector | `results.jsonl` |
| Scorers | score each result by the method its test type names | results, answer keys, corpus | scores and error labels |
| Reporter | builds the report, baselines and confidence intervals | scores | `report.html`, `report.json` |
| Exporters | write tests and scores into other tools | scores | Langfuse, LangSmith or Inspect records |

## Two connections, never one

- The corpus connector reads raw decisions from anything that can fetch a decision by id and find one by citation: a folder, S3, SQL, an HTTP API or an MCP server. Casebench caches fetched decisions locally, and the dry run counts the API calls a run needs. The agent may retrieve from the same corpus.
- The target connector reaches the AI under test. In pull mode, Casebench calls the target through HTTP, an OpenAI-compatible endpoint, MCP or a Python function. In push mode, the target's product logs question, answer and citations to Casebench, which scores them in the background.
- Casebench refuses a config where the corpus is the AI endpoint under test. A tool must not confirm its own citations. The same document API behind the agent and the checks is fine.

## Court test types

| Type | The AI gets | Answer key | Scoring | Error label on failure |
|---|---|---|---|---|
| Outcome | the facts and claims, operative part removed | the ruling (upheld, reversed, granted, rejected) | exact match | wrong outcome |
| Statute | the facts and the legal question | statute articles the court cited | precision and recall over the article set | missed statute, wrong statute |
| Precedent | the legal question | decisions the court cited | recall at k, nDCG | missed precedent |
| Statute version | a question fixed to a date | the article text in force on that date | exact match on version id | wrong statute version |
| Appeal | the lower court decision | the higher court's ruling on it | exact match | wrong outcome |
| Research | an open legal question built from the decision | the court's reasoning passage | reference-anchored judge | unsupported claim, wrong holding |
| Citation integrity | applies to every answer of every type | the corpus | lookup, then passage comparison | fabricated citation, misstated citation |

Outcome, statute, precedent, version and appeal need no LLM to score. The judge runs only on research tests and on the "does the passage support the claim" step of citation integrity.

## Integrity controls

| Threat | Control | Shown in the report as |
|---|---|---|
| Wrong answer key | two extraction models must agree; a disagreement excludes the test | agreement rate per field |
| Unreviewed key passes for approved | every case carries an approval state; drafts can be run at once, and the report keeps lawyer-approved and unreviewed rows apart | the approval state on every row |
| Model memorised the decision | `--after <date>` keeps only decisions after the model's training cutoff | the cutoff and how many tests it allowed |
| The target looks the answer up | research mode counts a lookup as success; reasoning mode excludes the source decision and marks any answer citing it as leaked | the mode and the leaked count |
| Question text gives the answer away | majority-class and text-only baselines on every objective type | baseline beside each score |
| Judge is unreliable | the judge also grades a sample of objective tests, and the report shows its agreement with exact scoring | judge agreement with exact scoring |
| Judge favours its own family | warning when judge and target share a model family | the warning |
| Noise passes for a difference | bootstrap confidence intervals; differences inside them are marked not significant | intervals and the marker |
| Target is nondeterministic | `--repeats n` runs each test n times | per-test agreement across repeats |
| Result cannot be reproduced | frozen suite with id, content hash, Casebench version and corpus snapshot id | the manifest |

## Data contracts

Decision record, one JSON object per line. Connectors produce it and everything downstream consumes only it.

```json
{"id": "tr-yargitay-9hd-2024-1234", "jurisdiction": "tr", "court": "Yargıtay 9. HD",
 "level": "appellate", "date": "2024-05-02", "text": "...",
 "metadata": {"docket": "2023/5678", "decision_no": "2024/1234"}}
```

Target config:

```yaml
target:
  type: http                      # http | openai_compatible | mcp | python | command | offline
  start: uv run uvicorn app:api --port 8000   # optional; runs under the capture wrapper
  url: https://ai.firm.internal/ask
  headers: {Authorization: "Bearer ${FIRM_TOKEN}"}
  body: {query: "{{question}}"}
  answer: $.answer
  citations: $.sources[*].ref     # optional; else parsed from the answer text
corpus: {type: s3, uri: s3://firm-decisions/tr/}
judge: {model: "<user's own provider and key>"}
network_allowlist: [ai.firm.internal, api.provider.example]
```

Result record, one per test per repeat:

```json
{"suite_id": "...", "test_id": "...", "repeat": 0, "answer": "...", "citations": ["..."],
 "scores": {"outcome": 1}, "errors": ["fabricated_citation"], "latency_ms": 2140}
```

## Non-functional requirements

| Area | Requirement |
|---|---|
| Privacy | runs on the user's machines; calls only allowlisted hosts; no telemetry; the shared place receives only what `casebench push` sends ([workbench.md](workbench.md)) |
| Resumability | every result is written before the next test starts; a rerun skips finished tests |
| Cost | `--dry-run` reports call and token estimates for target and judge before anything is sent |
| Scale | samples from corpora of any size through the connector; never loads the whole corpus |
| Distribution | a Python package with a CLI; the target can be in any language because it is reached over a connector |
| License | open core: Apache-2.0 core, source-available `ee/` team server ([open-source.md](open-source.md)) |
| Language | models do the language work, with no per-country parsers or word lists (decision 0024) |
| Model choice | extractor and judge go through one provider interface; users pick any model |
