---
title: Choose the judge
description: Pick the model that reads citations and grades criteria from the public model catalog, add a second judge from another family, and set model options by name.
sidebar:
  order: 6
---

The judge is a model you choose and pay for with your own key. It lists the citations in each answer, names the document each one means, decides whether that document supports the claim, and grades criteria. It never decides alone what exists: your corpus does.

Outcome suites need no judge. Everything else does. There is no default model.

## Find a model

`casebench models` lists the providers in the public model catalog, with the variable each one's key is read from. `casebench models PROVIDER` lists that provider's models. With `--json`, each model has its family, price per million tokens and context window:

```sh
casebench models --json
casebench models anthropic --json
```

```json
[
  { "id": "anthropic", "name": "Anthropic", "key": "ANTHROPIC_API_KEY", "models": 17 },
  { "id": "openai", "name": "OpenAI", "key": "OPENAI_API_KEY", "models": 52 },
  { "id": "openrouter", "name": "OpenRouter", "key": "OPENROUTER_API_KEY", "models": 390 }
]
```

```json
{
  "id": "claude-opus-5-5",
  "name": "Claude Opus 5.5",
  "family": "claude-opus",
  "price_per_million": { "input": 4, "output": 20 },
  "context": 1000000
}
```

These are excerpts from the catalog as read on 2026-10-26; the lists change as the catalog does. `--catalog FILE` reads a saved copy, for a machine without network access.

## Set it in `init`

At a terminal, `casebench init` shows a type-to-filter list of providers, then of models. Every choice is also a flag:

```sh
casebench init --judge-provider openai --judge-model gpt-5.5
```

It writes the provider plugin that speaks the provider's API, the variable its key is read from, the model's family and its context window. A key found in a `.env` file goes under `keys:`:

```yaml title="casebench.yaml"
judge:
  provider: openai
  model: gpt-5.5
  options:
    api_key_env: OPENAI_API_KEY
    family: gpt
  context_window: 1050000
keys:
  OPENAI_API_KEY: .env
```

A provider whose API is another's gets that plugin. OpenRouter documents its API as compatible with OpenAI's chat completions, so `--judge-provider openrouter` writes the `openai` provider with OpenRouter's address:

```yaml title="casebench.yaml"
judge:
  provider: openai
  model: google/gemini-3.1-pro-preview
  options:
    base_url: https://openrouter.ai/api/v1
    api_key_env: OPENROUTER_API_KEY
    family: gemini-pro
  context_window: 1048576
```

`--judge-option NAME=VALUE` sets an option over the catalog's. Unless you pass `--no-live`, `init` asks the judge one question before it writes the file.

## Prices are looked up, not written

`init` writes no price. `casebench run`, `casebench import` and `casebench extract` look each model's price up when they start: from OpenRouter's own list for a model called through OpenRouter or whose id is one of OpenRouter's, and from the model catalog for any other. The last lists read are kept in `.casebench/prices.json`, which git ignores, for when the network is out of reach. A model neither list has is reported as unpriced.

For a model on your own servers, write the price by hand. A price in `casebench.yaml` wins over the lists:

```yaml title="casebench.yaml"
judge:
  provider: openai
  model: firm-llm-70b
  options: { base_url: https://llm.firm.internal/v1, api_key_env: FIRM_LLM_KEY, family: firm }
  price: { input: 0.5, output: 1.5 }   # US dollars per million tokens
```

## Pick a judge from another family

A model grading its own family's answers favours them. Casebench compares families as the catalog gives them, never by reading a model's name. When it picks a judge from the catalog, `init` writes each model name it finds in your code under `agent_models:`, with its family:

```yaml title="casebench.yaml"
agent_models:
- model: claude-sonnet-4-5
  family: claude-sonnet
```

`init` warns when the judge shares a family with a model in your code. Every `casebench run` checks the judges against `agent_models:` again, and warns when the agent called a model the list does not name.

The catalog gives some vendors several families: `claude-sonnet` and `claude-opus` are different families, so a Claude Opus judge of a Claude Sonnet agent draws no warning. If you want a judge from another vendor, choose it by its provider.

## Add a second judge

A second judge must come from a different model family. With two, a criterion or a citation passes only when both pass it:

```yaml title="casebench.yaml"
judges:
  - provider: openai
    model: gpt-5.5
    options: { api_key_env: OPENAI_API_KEY, family: gpt }
  - provider: anthropic
    model: claude-opus-5-5
    options: { api_key_env: ANTHROPIC_API_KEY, family: claude-opus, max_tokens: 4000 }
```

Write `judge:` for one judge or `judges:` for two, not both. `casebench run` refuses two judges of the same family before it sends anything. Every disagreement is listed in the report and counted as failed until a lawyer decides it. Scores with two judges are stricter than with one, so they are not comparable with single-judge scores, and the score set says which.

## Set model options by name

Five settings have the same name for every provider that takes them. None has a default: what you do not set is not sent, and the provider's own default applies.

| Setting | What it controls |
| --- | --- |
| `reasoning_effort` | How much the model reasons, in the provider's own levels |
| `thinking_budget` | A token budget for reasoning, where the provider takes one |
| `temperature` | Sampling temperature |
| `max_tokens` | The output limit. The `anthropic` provider requires it. |
| `model_fields` | A model's own request fields, for the `bedrock` provider |

```yaml title="casebench.yaml"
judge:
  provider: anthropic
  model: claude-opus-5-5
  options:
    api_key_env: ANTHROPIC_API_KEY
    family: claude-opus
    max_tokens: 4000
    reasoning_effort: low
```

A setting a provider does not take is refused when the model is built, naming the settings it does take. `casebench check` asks each judge one short question with its settings and says whether the provider accepted them. When the provider answers 401 or 403, the check says the key was refused, names its variable and points at `casebench keys NAME`. The table of how each provider sends each setting is in [Judge providers](/integrations/models/judge-providers/).

## Allow the judge's host

A judge's provider address is a host the run may call: its `base_url`, or the provider's default, such as `api.openai.com`. It needs no entry under `network: allow:`. The `google`, `bedrock` and `azure` providers call through the vendor's own SDK, which Casebench does not see. See [Allow the hosts your agent calls](/developers/guides/setup/network/).

## How many candidates the judge sees

`candidates` is how many search results the judge may match one citation against, 5 unless you set it. A cited document the store ranks lower is reported as unresolved, so the report's unresolved count is the figure to watch before you raise it.

## Related

- [How citation checks work](/developers/concepts/citation-checks/).
- [Comparable runs](/developers/concepts/comparable-runs/): why a new judge or prompt makes two runs not comparable.
