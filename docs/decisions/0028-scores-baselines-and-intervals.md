---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Scores carry a bootstrap interval and a baseline; outcome scores need no model

## Context and problem statement

A score without its baseline hides how much the question text gives away (Multi-Legal-Bench found such leakage), and a score without an interval passes noise off as a difference. An outcome case has one right label, so scoring it must be exact and free. A run must be priced before anything is sent.

## Considered options

- scipy's bootstrap for intervals, scikit-learn's naive Bayes for the text-only baseline, exact label matching for outcomes
- Hand-written bootstrap and classifier on the standard library
- Normal-approximation intervals

## Decision outcome

Chosen option: "scipy and scikit-learn", because both are the standard, maintained implementations and the user chose libraries over own code.

- **Outcome scoring.** The `outcome` metric finds the shared outcome labels ([0027](0027-answer-keys-from-decisions.md)) in the answer. Exactly one label: correct or "wrong outcome". None or several: "unreadable outcome". No model is called.
- **Intervals.** Every mean score carries a 95% bootstrap confidence interval from `scipy.stats.bootstrap` with its defaults: 9,999 resamples and the BCa method. The random state is derived from the suite id, so a report is the same on every machine. 95% is the convention the report states; nothing else is configurable yet.
- **Comparing two runs.** `casebench compare` pairs the two runs' scores case by case and bootstraps the mean difference. A difference whose interval contains zero is marked not significant.
- **Baselines** for outcome suites: the majority class (always answering the suite's most common ruling) and a text-only baseline: a multinomial naive Bayes classifier (scikit-learn, default add-one smoothing) on the words of the facts, scored leave-one-out across the suite. Both are shown beside the score.
- **Report.** After a run is scored, the terminal shows one table per task and metric with n, the mean, its interval and the baselines. `report.json` holds the same numbers and every label, beside the run's `results.jsonl` and score sets.
- **Dry run.** `casebench run --dry-run` counts the target calls (cases not yet stored) and the judge calls a run needs at least: one per answer to list its citations, plus two per citation found, which is unknown until the answers exist. With a corpus configured it states the corpus calls per citation (one search, up to `candidates` fetches) and how many documents are already cached and cost no call. It estimates input tokens at four characters per token, OpenAI's published rule of thumb for English text, and says the estimate is rough and varies by language. Nothing is sent.

### Consequences

- Good, because two numbers that differ by noise are labelled as such, and leaked labels show as a high text-only baseline.
- Bad, because numpy, scipy and scikit-learn add roughly 100 MB to an install.
- Bad, because the token estimate is rough; providers' own counters would need the text sent.

## Revisit when

A user needs another confidence level or method, or the token estimate misleads users in a measured way.

## More information

- [scipy.stats.bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
- [scikit-learn MultinomialNB](https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.MultinomialNB.html)
- [OpenAI: what are tokens](https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them)
- [Multi-Legal-Bench](https://arxiv.org/abs/2605.29738)
