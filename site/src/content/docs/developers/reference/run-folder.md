---
title: Run folder
description: What a run writes to disk, file by file, which files are append-only, and what else lives under .casebench/.
sidebar:
  order: 4
---

A run is a folder under `--runs-dir`, `.casebench/runs/` by default, named by its run id. Every file is plain JSON or JSON Lines, so any language can read it and a diff shows what changed. Casebench replaces each key's value in what it writes to `run.json`, `results.jsonl`, `judge.jsonl`, the score sets, `report.json`, `reviews.jsonl` and `preferences.jsonl`.

```text
.casebench/runs/after-prompt-fix/
├── run.json
├── results.jsonl
├── judge.jsonl
├── scores/
│   └── 20261026T195658Z-9fb4283b4adc4504aa607d33865261ba.jsonl
├── report.json
├── reviews.jsonl
└── preferences.jsonl
```

The examples on this page come from that run, scored by Casebench 0.5.1 with a scripted judge, so the token counts are zero.

## `run.json`

What ran against what, written when the run starts.

```json
{
  "run_id": "after-prompt-fix",
  "suite_id": "employment",
  "suite_hash": "sha256:645a2d35171a6a412f5667ded0befc78a9e222b9d076b6c7e8d3321e9f6e61bc",
  "target": "python",
  "casebench_version": "0.5.1",
  "commit": null,
  "unattributed_calls": 0
}
```

`commit` is the commit the agent's code was at: `--commit`, else `GITHUB_SHA`, else the commit checked out in the folder the run started from, else `null`. `unattributed_calls` counts the captured calls no case could claim, which happens when several cases run at once and a call carries no trace context; the run's last lines say so when it is above zero. A run made with `casebench import` from a spreadsheet of answers has `offline` as its target.

## `results.jsonl`

One line per case per repeat, appended as each finishes and before the next starts. A rerun with the same run id skips the cases already here.

```json
{"case_id":"probation","repeat":0,"output":"No reason is needed while the probation period lasts (CA 2023/07), but one week's notice is still owed.","citations":[],"documents":[],"steps":[],"error":null,"latency_ms":0.3721248358488083}
```

`steps` holds the captured model calls, tool calls, retrievals, reranks, document fetches and gaps of that case. `error` holds why the target failed on the case.

## `judge.jsonl`

One line per judge question: its key, the judge's parsed reply and, since 0.2.0, the provider, model and tokens of the call that made it. The key is a SHA-256 of the provider, the model and the two prompts. Re-scoring reads a reply back instead of asking again, and two metrics that list one answer's citations ask once.

```json
{"key": "49108120ac1135494bfe0fb183465bd64654b73237d4a0c9c63960c1685e83aa", "reply": [{"citation": "CA 2024/11", "claim": "A dismissal given only by telephone is void: Examplia requires a dismissal in writing (CA 2024/11).", "kind": "decision", "jurisdiction": null}], "usage": {"provider": "anthropic", "model": "demo-judge", "input_tokens": 0, "output_tokens": 0}}
```

The report's `spend` counts the judge's calls from these lines, and the agent's from the model-call steps in `results.jsonl`. A line written before replies recorded usage counts as a call of an unknown model, with no tokens and no price.

## `scores/`

One file per scoring pass, named by when it was written. Its first line says what produced it; every other line is one score, or one result a metric could not score. A score set is never rewritten: scoring again writes a new one.

```json
{"produced_by": {"casebench_version": "0.5.1", "metrics": {"citation_integrity": {"version": "3", "reads": ["corpus", "judge"]}, "criteria": {"version": "1", "reads": ["judge"]}}, "judges": [{"provider": "anthropic", "model": "demo-judge", "family": "demo", "candidates": 5}], "prompts": {"list_citations": "0766ac5a…", "match": "52b40e64…", "weigh": "f9b5ae16…", "grade": "35540359…"}, "corpora": {"corpus": "folder-fbaca627…"}, "extracted_by": ["anthropic/model-a", "openai/model-b"]}}
{"case_id":"written-notice","repeat":0,"metric":"criteria","metric_version":"1","kind":"llm","direction":"higher","value":1.0,"label":"all criteria passed", ...}
{"scoring_error": {"case_id": "...", "repeat": 0, "metric": "criteria", "error": "..."}}
```

The hashes are shortened here. A `scoring_error` line appears only when a metric failed on a result, such as a judge call that still failed after its retries.

## `report.json`

The latest score set's tables, citation counts, error rates, spend, judge agreement, calibration, authority funnel and every score, in the [report format](/developers/reference/formats/report/). It is the file to copy back from a machine that ran Casebench. `casebench report RUN_DIR` prints it again, counting lawyers' verdicts given since.

## `reviews.jsonl`

Lawyers' verdicts on single criteria, one line each, appended. `casebench review criterion`, the workbench's review queue, `casebench import` of a review spreadsheet and `casebench pull` from a team server write them.

```json
{"case_id":"probation","repeat":0,"criterion_id":"c2","verdict":"fail","judge":"pass","note":"It says notice is owed but not that it is one week.","by":"A. Lawyer","at":"2026-10-26T20:20:20+00:00"}
```

`judge` is what the judge said. A verdict that overrules the judge needs a `note`. The report counts verdicts against the judge's under `calibration` at once, and the next scoring of the run puts each lawyer's latest verdict in place of the judge's.

## `preferences.jsonl`

Lawyers' blind choices between two runs' answers to one case, one line each, appended. A choice is kept in the later run's folder, and `against` names the earlier run.

```json
{"against":"before-prompt-fix","case_id":"overtime","repeat":0,"shown_as_a":"second","choice":"second","reason":"Gives the five-year limit CA 2022/31 sets and when it runs; the other says two years.","by":"Ayşe Yılmaz","at":"2026-10-26T19:57:54+00:00"}
```

`shown_as_a` is which run's answer was shown as A. `choice` is `first`, `second` or `equal`. The workbench's compare view and `casebench pull` write them.

## What a team server receives

`casebench push` sends `run.json`, `results.jsonl` without its steps, the score sets, `report.json`, `reviews.jsonl` and `preferences.jsonl`. `judge.jsonl` stays on your machine. With `--traces`, each step goes too, as its kind, name, model, document ids, token counts and times, never what it said. `casebench pull` merges the lawyers' new lines into `reviews.jsonl` and `preferences.jsonl`, and never replaces a line.

## Elsewhere under `.casebench/`

| Path | Holds |
| --- | --- |
| `.casebench/keys/` | `keys.jsonl` and `extraction.json` from `casebench extract`, by default |
| `.casebench/suites/first/` | The suite the first `casebench run` with no `--suite` builds |
| `.casebench/corpus-cache/<corpus key>/` | Fetched documents, and kept searches under `searches/` |
| `.casebench/prices.json` | The last price lists read, used when they cannot be read again |
| `.casebench/casebench.schema.json` | The schema an editor checks `casebench.yaml` against |
| `.casebench/target.py` | The adapter a coding agent writes for a Python target, when the setup has one |
| `.casebench/casebench.db` | The workbench's SQLite database, with its event log |
| `.casebench/.env` | Keys typed into the workbench, when `keys:` names no file git ignores for them |
| `.casebench/team.db` | A trial team server's SQLite database |

Keep `.casebench/` out of git apart from the adapter and the schema. A `.casebench/.gitignore` holding these lines does it:

```text
*
!.gitignore
!target.py
!casebench.schema.json
```
