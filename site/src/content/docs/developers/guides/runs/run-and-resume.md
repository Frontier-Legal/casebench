---
title: Run a suite, and resume one
description: Build a first suite with one command, run a frozen suite, price it first with a dry run, resume after an interruption, and read what the run spent and its error rates.
sidebar:
  order: 1
---

`casebench run` sends every case of a frozen suite to your agent, stores each result before the next case starts, then scores the run and prints its report.

## The first run builds its own suite

With no `--suite`, `run` uses the suite at `.casebench/suites/first`. When that suite does not exist yet, the run builds it from your corpus:

1. It extracts answer keys from a sample of decisions with the two extraction models under `extract:`.
2. It generates the suite from those keys: outcome cases, plus statute and precedent cases when a judge is set.
3. It runs the suite.

Before it spends anything, it prints what extraction will cost and how many cases it will send, and asks you to go on:

```sh
casebench run
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--sample N` | `20` | How many decisions the first run reads |
| `--cases N` | `10` | How many cases it makes |
| `--yes` | | Build the suite without asking |

With no terminal and no `--yes`, the run stops before it spends anything and says to pass `--yes`. That is how a script or a coding agent shows you the estimate first.

The first run needs `corpus:` and `extract:` in `casebench.yaml`, which `casebench init` sets. Without them it stops and tells you to add them or pass `--suite`. With several corpora, the first suite comes from the first one the config names. To mix corpora, build the suite with `casebench extract` and `casebench generate`.

Each step keeps what it made. Run `casebench run` again after an interruption: it skips extraction when the keys exist in `.casebench/keys/`, skips generation when the suite exists, and resumes the last run of that suite that stopped before every case was answered.

## Run a suite you have

```sh
casebench run --suite suites/employment --run-id court-1
```

The run lives in `.casebench/runs/court-1/`. See [Run folder](/developers/reference/run-folder/) for what is in it. Without `--run-id`, the run is named after the time it started and a random suffix.

## Price it first

```sh
casebench run --suite suites/employment --dry-run
```

A dry run sends nothing to the agent, the judge or the corpus. It counts:

```text frame="terminal"
target: 7 calls (0 cases already stored), about 219 input tokens
judge: at least 7 calls and 1463 input tokens (one call per answer to list its citations, then one to match them all and one per citation to weigh it, known only once the answers exist)
judge: 7 calls to grade criteria (one per answer for each judge) and at least 1679 input tokens before the answers
corpus: one search per citation and up to 5 document fetches each; 6 documents and 0 searches already cached cost no call
tokens are rough: 4 characters per token, and it varies by language
nothing was sent
```

Token counts are estimated at four characters per token. With no `--suite`, a dry run needs the first suite to exist already.

## Resume

Every result is written before the next case starts. If a run stops, for a crash, a rate limit, a refused host or Ctrl-C, run it again with the same id:

```sh
casebench run --suite suites/employment --run-id court-1
```

Cases already stored are skipped, so you pay only for the rest. A result a metric could not score, such as one whose judge call failed, is listed under scoring errors, and running again with the same `--run-id` scores only what is missing. Scoring again reads the judge's kept replies in `judge.jsonl` and asks the judge nothing it already answered.

## What the report prints

After the tables, a run prints its error rates, what it spent, and where to open it:

```text frame="terminal"
fabricated citation: 14% of 7 answers [0%, 57%], cites a decision or statute the corpus does not hold
unsupported claim: 14% of 7 answers [0%, 57%], cites an authority the corpus holds for something it does not say
spend: $0.00 · agent $0.00 · judge $0.00
  judge anthropic/demo-judge      26 calls            0 in           0 out  $0.00
  only model calls are counted; search APIs and other services the agent pays for are not.
.casebench/runs/after-prompt-fix/report.json
open it in the workbench: casebench ui --runs-dir .casebench/runs
```

This output is from a project whose judge is a local stand-in that costs nothing. A real run prints dollar amounts.

### Error rates

Each rate is the share of answers with that error, with its 95% interval, over the answers the error could occur in:

| Error | An answer has it when |
| --- | --- |
| fabricated citation | It cites a decision or statute the corpus does not hold |
| unsupported claim | It cites an authority the corpus holds for something it does not say |
| wrong outcome | It states a ruling other than the court's or the lawyer's, or none |
| wrong statute | It relies on a statute the court did not apply |

A rate is printed only when the run had answers it applies to. A lawyer's verdict replaces the judge's before the rates are counted, so `casebench report` prints rates that include verdicts given since the run was scored. In the workbench each rate opens the answers behind it.

### Spend

The spend lines give one line per model, marked as the agent's or the judge's, with its calls, tokens and cost, then the agent's total, the judge's total and the run's total.

- The agent's spend comes from the model calls the run recorded. A recorded model is matched to an entry under `agent_models:` by its id, by its last path segment, or as a dated version of it.
- The judge's spend comes from the tokens kept beside each reply in `judge.jsonl`. Scoring again adds nothing.
- Prices are looked up when the run starts: OpenRouter's own price for a model it sells, else the public model catalog's. The last lists read are kept in `.casebench/prices.json` for when the network is out of reach. A `price:` you write in `casebench.yaml` wins, for a model on your own servers.
- A model with no price is reported with its tokens and named as unpriced, never counted as free.
- Only model calls are counted. Search APIs and other services your agent pays for are not.

## Concurrency

```sh
casebench run --suite suites/employment --max-concurrency 8
```

The default is one case at a time, so a run never loads your agent harder than you asked. `--max-concurrency` overrides the target's own `max_concurrency`.

## Progress without a terminal

In CI or a log, where output is not a terminal, `run` prints one line per case answered and per case scored, each with its time and the judge's running cost:

```text frame="terminal"
answered 1/1 x1 in 0.0s
scored 1/1 x1 in 0.0s, judge $0.00 so far
```

## The commit a run ran at

`run.json` records the commit the agent's code was at: `--commit` when you pass it, else the `GITHUB_SHA` variable GitHub Actions sets, else `git rev-parse HEAD` in the current folder, else none. A baseline and a later run then each name their code.

## Run a function without a config

```sh
casebench run --suite suites/employment --python agent.py:answer
```

`--python` runs a Python agent's function, `answer` by default. With a `casebench.yaml` present, it replaces only the target.

## Hosts the run may call

A run calls only the hosts `casebench.yaml` names and those under `network: allow:`. A call to any other host stops the run, and the case is sent again when you resume after allowing it. See [Allow the hosts your agent calls](/developers/guides/setup/network/).

## Print the report again

```sh
casebench report .casebench/runs/court-1
```

## Related

- [Compare two runs](/developers/guides/runs/compare-runs/).
- [Gate a pull request on a run](/developers/guides/runs/gate-in-ci/).
- [Run where the agent is reachable](/developers/guides/runs/run-elsewhere/).
