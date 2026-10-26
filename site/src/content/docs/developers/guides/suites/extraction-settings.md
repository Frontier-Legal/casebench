---
title: Choose extraction settings by measurement
description: Price an extraction before you run it, then compare model settings on the same decisions by agreement, time and cost.
sidebar:
  order: 3
---

Extraction reads every decision twice, with two models. On a corpus of thousands of decisions, a reasoning setting can decide whether that costs tens or hundreds of dollars. Casebench recommends no setting. It gives you the numbers to choose one.

## Price it before you spend

```sh
casebench extract --sample 200 --dry-run
```

The dry run calls no model and no document store. It reads the two public price lists, as every extraction does, then states the decisions, the model calls, two per decision, and a cost range:

- at least the input, estimated at four characters per token from the decisions already cached;
- at most that plus each call's `max_tokens` of output.

This is the output for a folder of six short sample decisions, with both models at `max_tokens: 8000`, priced from the lists read on 2026-10-26:

```text
extract: 200 decisions, 400 model calls (one per decision for each of the 2 models)
input: about 326 tokens per call, from the 6 decisions already cached
cost, an estimate: from $0.28 (input alone) to $40.28
tokens are rough: 4 characters per token, and it varies by language
nothing was sent
```

The output limit dominates the upper bound, so set `max_tokens` to what an extraction needs. A model with no `max_tokens` leaves the range with no upper bound, and the dry run names it. With no decision cached yet, the input is unknown, and the lower bound counts none of it: run `casebench corpus check` first to fetch a sample.

### Where the prices come from

Each model's price comes from OpenRouter's own list when the model is called through OpenRouter or named by an OpenRouter id, and from the public model catalog otherwise. The last lists read are kept in `.casebench/prices.json` and used when the network is out of reach. A `price:` you write in the model's block wins over both. A model no list has and no `price:` names is reported with its tokens and an unknown cost.

## Try a setting on a small sample

`--set NAME=VALUE` overrides a model setting for both extraction models, for one run. The names are `reasoning_effort`, `thinking_budget`, `temperature`, `max_tokens` and `model_fields`, and each value is read as YAML, so numbers stay numbers. A setting a provider does not take stops the extraction before any model is called.

```sh
casebench extract --sample 10 --out .casebench/keys-low --set reasoning_effort=low
casebench extract --sample 10 --out .casebench/keys-default
casebench compare .casebench/keys-low .casebench/keys-default
```

`--set` works with `--dry-run` too: `--set max_tokens=4000` moves the upper bound before you spend. The dry run does not estimate what a reasoning setting adds. Use the same sample for both runs, so the comparison is about the setting and not the decisions: a store that can list its documents gives the same sample for the same `--sample`, and a store that cannot gives it for the same `--query`.

`compare` prints each folder's settings, then side by side the agreement per field as agreed decisions out of those read, the keys kept, the median time a decision took, and the cost in all and per decision.

## What to look at

| Figure | Why it matters |
| --- | --- |
| Agreement per field | Lower agreement means fewer keys per decision, so a cheaper setting that loses half the statute keys may cost more per usable case. |
| Time per decision | It decides how long a full extraction takes at your `--max-concurrency`. |
| Cost | The two models rarely cost the same. Each keys folder's `extraction.json` keeps every model's calls, tokens and cost, with the settings it ran with, so the choice can be checked later. |

## Related

- [Choose the judge](/developers/guides/connect/judge/) for the setting names each provider takes.
- [Judge providers](/integrations/models/judge-providers/) for how each provider sends each setting.
- [Court-derived references](/developers/concepts/court-references/) for how agreement is decided.
