---
title: Compare two runs
description: Tell whether a change to your agent moved a metric, with the interval of the difference, every setting that makes two runs not comparable, and lawyers' blind preferences between the two.
sidebar:
  order: 2
---

After you change a prompt, a model or a retriever, run the same suite again and compare the two runs:

```sh
casebench run --suite suites/employment --run-id after-prompt-fix
casebench compare .casebench/runs/before-prompt-fix .casebench/runs/after-prompt-fix
```

Both runs must have run the same suite, checked by its content hash. Comparing runs of different suites is refused:

```text frame="terminal"
Error: the two runs ran different suites; compare runs of one suite
```

## What it prints

One line per task and metric: the score before and after, how many cases were paired, the 95% interval of the difference, and whether the difference is significant.

```text frame="terminal"
qa · citation_integrity: 43% -> 71% over 7 cases, difference +14% to +86%, significant
qa · criteria: 61% -> 100% over 7 cases, difference +11% to +75%, significant
```

Casebench pairs the two runs' scores case by case and bootstraps the mean difference. A difference whose interval contains zero is marked not significant. Seven cases leave wide intervals, as above.

`compare` reads each run's latest score set, with a lawyer's verdict on a criterion in place of the judge's, and counts every case, approved or not. [`casebench gate`](/developers/guides/runs/gate-in-ci/) is the stricter comparison: by default it pairs only lawyer-approved cases.

## Lawyers' blind preferences

Lawyers can compare the same two runs in the workbench's **Compare runs** page. They read each pair of answers as A and B without knowing which run wrote which, choose one or call them equal, and give a reason. Each preference is kept in the second run's folder, in `preferences.jsonl`.

When lawyers have compared the two runs, `compare` prints their summary after any settings that differ:

```text frame="terminal"
lawyers compared the answers blind, the second run against the first:
  employment: 4 wins, 0 losses, 3 ties over 7 pairs, mean +0.57 [+0.14, +0.86], not significant
```

The summary is per practice area. The mean scores a win +1, a loss -1 and a tie 0, and the interval is a 95% bootstrap interval. A difference is significant only when that interval leaves out zero and an exact two-sided sign test of wins against losses, ties left out, gives p below 0.05. Here the interval leaves out zero, but four wins and no losses are too few for the sign test, so the line says not significant.

The order of the two runs matters: preferences are read from the second run's folder, and wins are the second run's.

## When the runs were scored differently

A score depends on more than your agent. Each score set records what produced it: the Casebench version, each metric's version, the judge's provider, model and family, a hash of each judge prompt, each corpus, and the models that extracted the answer keys. When those differ, `compare` lists them first and marks the metrics each one moves:

```text frame="terminal"
the two score sets were produced differently:
  judge: openai/gpt-5.5 (gpt family, 5 candidates) -> anthropic/claude-sonnet-5-5 (claude-sonnet family, 5 candidates)
statute · statute: 58% -> 66% over 96 cases, difference +1% to +14%, significant; not comparable, because of judge
```

The figures above are illustrative. They are still shown. "Not comparable" means the change could come from the judge rather than your agent.

| Changed | Moves |
| --- | --- |
| A metric's version | That metric |
| The judge or its prompts | The metrics that read the judge |
| A corpus | The metrics that read the corpus |
| The extraction models | Every metric |
| The Casebench version alone | Nothing. A metric that scores differently gets a new version. |

## Compare two extractions

Given two keys folders instead of two runs, `compare` puts their extractions side by side: the model settings, the agreement per field, the time and the cost. Use it to choose extraction settings by measurement:

```sh
casebench extract --sample 20 --out .casebench/keys-low --set reasoning_effort=low
casebench extract --sample 20 --out .casebench/keys-default
casebench compare .casebench/keys-low .casebench/keys-default
```

## See every run of a suite

The workbench's **History** page charts each metric and error rate of a suite run by run, with its interval and by practice area, and marks the runs whose settings make them not comparable. Open it with `casebench ui`.

## Related

- [Gate a pull request on a run](/developers/guides/runs/gate-in-ci/).
- [Scores, intervals and baselines](/developers/concepts/scores/).
- [Comparable runs](/developers/concepts/comparable-runs/).
- [Compare two versions](/lawyers/guides/compare-versions/), for your lawyers.
