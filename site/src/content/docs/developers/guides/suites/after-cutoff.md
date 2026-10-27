---
title: Test only on decisions after a training cutoff
description: Keep a model from scoring well because it memorised the decision, by generating suites only from decisions published after its training cutoff.
sidebar:
  order: 2
---

A model may have read a published decision during training. If it did, it can answer the case from memory, and the score measures recall rather than legal reasoning. Decisions keep arriving, so with a current corpus you can always build a suite from decisions the model cannot have seen.

## Generate after the cutoff

```sh
casebench generate --suite-id labour-2026h1 --out suites/labour-2026h1 \
  --keys .casebench/keys --n 80 --after 2026-01-31
```

`--after` keeps only answer keys from decisions dated after that day. A key whose decision has no date is left out too. Use the training cutoff your model provider publishes for the model under test.

`generate` prints how many decisions the cutoff allowed and how many it excluded, in a line such as this one, whose figures are illustrative: `cutoff 2026-01-31: 112 decisions allowed, 2384 excluded`. The suite's manifest records the same under `generation`, as `after`, `decisions_allowed` and `decisions_excluded_by_date`, so a reader of the report can check it. A suite that mixes corpora with `--corpus NAME=COUNT` records them per corpus, under `generation.corpora`, and prints no such line.

## Extract enough recent decisions

`--after` filters keys that already exist. If most of your corpus is older, extract from recent decisions first.

- A store that can list its documents is sampled from its whole listing, in a stable order, so a larger `--sample` gives you more recent decisions in proportion.
- A store that cannot list its documents is sampled through searches. Search for recent ones:

```sh
casebench extract --sample 150 --query "2026"
```

An extraction from a corpus replaces the keys an earlier extraction from the same corpus left in that folder. Keys from other corpora stay. To keep both sets, pass `--out` a folder of its own, and `--keys` that folder to `generate`.

Price the extraction first with `--dry-run`; see [Choose extraction settings by measurement](/developers/guides/suites/extraction-settings/).

## Watch the baselines too

A suite can leak its answer through the question text as well as through training. Every outcome table shows two baselines: the majority class, and a text-only classifier that reads only the facts. If the text-only baseline scores close to your agent, the facts give the ruling away, whatever the cutoff.

## Related

- [Scores, intervals and baselines](/developers/concepts/scores/).
- [Court-derived references](/developers/concepts/court-references/).
