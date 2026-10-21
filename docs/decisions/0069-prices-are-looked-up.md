---
status: accepted
date: 2026-10-21
decision-makers: Casebench maintainers
---

# A model's price is looked up from where it is sold when a command needs it, and never written into casebench.yaml

Replaces the prices that [0032](0032-provider-catalog-and-sdk-providers.md) and [0051](0051-what-a-run-spends.md) had init and the workbench copy into `casebench.yaml`. Amends rule 5 of AGENTS.md and [0046](0046-the-perimeter.md): two public price lists are read besides the agent and the judge.

## Context and problem statement

A price copied into `casebench.yaml` when a model is picked is frozen there: it goes stale when the seller changes it, and it is a number people read in their config without having chosen it. The operator decided on 2026-10-21 that prices are not written there and are looked up from their source instead.

Checked on 2026-10-21: OpenRouter lists every model it serves with its price through its own API (`GET https://openrouter.ai/api/v1/models`, US dollars per token, no key). OpenAI, Anthropic, Google, Bedrock and Azure publish no price through an API: their model lists need a key and carry ids and names only. The public model catalog ([0032](0032-provider-catalog-and-sdk-providers.md)) is the one machine-readable list of their prices.

## Considered options

1. Look prices up when a command needs them: a model OpenRouter sells, or whose id is OpenRouter's, at OpenRouter's own price; any other at the catalog's. Keep the last lists read, for when the network is out of reach. A price written in `casebench.yaml` still wins, for a model no list has.
2. Keep copying prices into `casebench.yaml`, and refresh them on `casebench init`.
3. Only the cost a provider reports with each answer.

## Decision outcome

Chosen option 1, because each price is the seller's current one and the config holds only what people chose. Option 2 keeps stale numbers in the file between refreshes. Option 3 leaves every provider but OpenRouter without a cost.

- **When.** `casebench run`, `casebench import` and `casebench extract` read both lists before they hold the run to its hosts ([0046](0046-the-perimeter.md)). The workbench prices from the last lists at once, and reads fresh ones in the background. `casebench check` and the other commands read none.
- **What is sent.** Two GET requests for public lists; nothing of the user's goes with them.
- **Out of reach.** The last lists read are kept in `.casebench/prices.json`, which git ignores, and used when a list cannot be read; a model neither list has is reported as unpriced, as before.
- **Written by hand.** `price:` stays a valid setting, for a model on the team's own servers.

### Consequences

- Good, because a run's spend is at the seller's price on the day it ran.
- Good, because `casebench.yaml` holds no number nobody chose.
- Bad, because a run starts with two more requests, about three seconds for the catalog's 5.9 MB list (measured 2026-10-21).

## Revisit when

- OpenAI, Anthropic or Google publish prices through an API: then theirs come from there.
