---
title: Scores, intervals and baselines
description: Why every score carries a 95% interval and its baselines, what the strict pass rate adds, and why Casebench reports no single accuracy number.
sidebar:
  order: 5
---

A score alone invites two mistakes: reading noise as a difference, and reading a leaky question as a smart agent. Casebench prints every score with what you need to avoid both.

## No single number

Results are reported per task, per metric, per reference source, per approval state and per jurisdiction. Casebench never averages across them. Court-derived and lawyer-written cases measure different things, unreviewed answer keys are not yet evidence, and a score for Turkish labour law says nothing about Norwegian tenancy. One number across all of those would be easy to quote and impossible to interpret.

## Intervals

Every mean score carries a 95% bootstrap confidence interval: 9,999 resamples with the BCa method, from `scipy.stats.bootstrap` with its defaults. Where BCa cannot be computed, the percentile method is used, and with one case or no variation the interval is the score itself. The random state is derived from the suite id, so a report gives the same interval on every machine.

Read the interval before the score. 70% on 40 cases with an interval of 55% to 83% is a weaker claim than 64% on 400 cases with 59% to 69%.

## Baselines

Outcome tables carry two baselines:

| Baseline | What it is | What a high value means |
| --- | --- | --- |
| `majority` | Always answering the suite's most common ruling | The suite is unbalanced |
| `text-only` | A naive Bayes classifier on the words of the facts, scored leave-one-out across the suite | The facts give the ruling away |

An agent is doing legal work only to the extent it beats both, by more than the interval.

## Strict pass rate

For metrics whose cases carry criteria, the report adds `all passed`: the share of answers that met every positive criterion and triggered no negative one, with its own interval. It sits beside the weighted score and never replaces it.

A weighted score of 90% can hide that most answers missed one material point. In legal work an answer that misses something material is wrong, not mostly right. The two numbers together show both how close the answers came and how many were complete.

## Error rates

Besides scores, a run reports four error rates, each the share of answers with the error and its 95% interval, over the answers the error could occur in:

| Error | An answer has it when |
| --- | --- |
| Fabricated citation | A citation names a decision or statute the corpus does not hold |
| Unsupported claim | A citation the corpus holds does not support the claim made with it |
| Wrong outcome | It states a ruling other than the court's or the lawyer's, or none |
| Wrong statute | The statute metric found a statute the court did not apply |

Each rate lists its failing answers, and in the workbench each opens beside its evidence.

## Lawyers' verdicts replace the judge's

A lawyer's verdict on a criterion, given in the workbench, in a review spreadsheet or with `casebench review criterion`, replaces the judge's in the report, the error rates, the history and the gate, without scoring the run again. The score set keeps the judge's verdicts, and the report's calibration counts, per kind of criterion, how often lawyers agreed with the judge and how often they overruled it.

## Outcome scores need no model

An outcome case has one right label. The `outcome` metric finds the shared outcome labels in the answer. Exactly one: correct, or "wrong outcome". None, or several: "unreadable outcome". No judge is called, so outcome scores are free and exact.

## Comparing two runs

`casebench compare` pairs two runs' scores case by case and bootstraps the mean difference. A difference whose interval contains zero is marked not significant. When lawyers compared the two runs blind in the workbench, it also prints their wins, losses and ties per practice area, called significant only when the interval leaves out zero and an exact sign test agrees. See [Compare two runs](/developers/guides/runs/compare-runs/). `casebench gate` fails a build only on a significant drop; see [Gate a change in CI](/developers/guides/runs/gate-in-ci/).

## Related

- For lawyers: [What a score means](/lawyers/concepts/scores/).
- [Report format](/developers/reference/formats/report/).
