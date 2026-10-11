---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Two models extract each answer key; a field counts only where their quotes agree

## Context and problem statement

A court decision holds the correct outcome, the statutes applied and the decisions relied on. Reading them out takes a model ([0024](0024-no-jurisdiction-adapters.md)), and a model can misread. A wrong answer key is worse than no key: it marks a correct agent wrong. The agreement rate is also R0's gate, so it must be measured the same way for every corpus.

## Considered options

- Two different models extract each decision independently; a field becomes a key only where both agree, judged by where in the decision each quoted its evidence
- One model extracts, a second checks it
- Two models, agreement judged by comparing the extracted strings

## Decision outcome

Chosen option: "two independent extractions, agreement by quoted passage", because two quotes from the same place in the text are the same evidence whatever language or citation format the decision uses, while two strings can differ in spelling and still mean one statute.

- **What a model returns.** For one decision, as JSON: the outcome as one label from a shared vocabulary (`upheld`, `reversed`, `partly_reversed`, `remanded`, `granted`, `rejected`, `partly_granted`, `dismissed`) with a quote; each statute and each decision relied on, as written, with a quote; and the facts written out without the ruling.
- **Evidence.** Casebench finds each quote in the decision's text and records its span. An item whose quote is not in the text has no evidence and is dropped.
- **Agreement, per field.** Outcome: both labels equal. Statutes and precedents: every item of one model overlaps the span of an item of the other, both ways. A field the models disagree on gets no key for that decision. Facts are written by the first model and kept only if they quote neither the outcome passage nor the label; they are the question, not a key.
- **Two different models.** The config names exactly two, and they must differ.
- **Storage.** `casebench extract` writes `keys.jsonl` (one answer key per decision, agreed fields only, each fact with its span) and `extraction.json` (per-field attempts, agreements and rates, and each model's tokens), so cost per 1,000 decisions is measured, not guessed.
- **Generating.** `casebench generate` turns keys into cases by type (`outcome`, `statute`, `precedent`), keeps only decisions dated after `--after` when given, balances across court levels with `--stratify court` using the levels the provider supplies, and freezes the suite ([0015](0015-suite-and-run-log-formats.md)). The manifest records the cutoff and how many decisions it allowed.

### Consequences

- Good, because a key exists only where two models found the same evidence, and every fact links to its passage.
- Bad, because two models cost twice one; `extraction.json` reports the tokens so the cost can be weighed.
- Bad, because a decision the two models read differently contributes no key for that field; the agreement rate shows how many.

## Revisit when

Measured agreement is high enough that one model and a sampled check would do, or so low on a field that the field is not worth keeping.

## More information

- [Swiss-Judgment-Prediction](https://arxiv.org/abs/2110.00806): court outcomes as labels.
- [Multi-Legal-Bench](https://arxiv.org/abs/2605.29738): label leakage from the case text.
