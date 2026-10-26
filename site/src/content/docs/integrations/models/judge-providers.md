---
title: Judge providers
description: The model providers Casebench calls for its own judge and extraction models, their options, how each sends the shared model settings, and where prices come from.
sidebar:
  order: 1
---

Casebench calls a model for its own work, judging and extraction, through a provider plugin. Five ship built in.

| Provider | Reaches | Calls through | Key |
| --- | --- | --- | --- |
| `openai` | OpenAI, and any OpenAI-compatible endpoint by `base_url`, such as OpenRouter | HTTP, Chat Completions | `api_key_env`, default `OPENAI_API_KEY` |
| `anthropic` | Anthropic, and Anthropic-compatible endpoints by `base_url` | HTTP, Messages | `api_key_env`, default `ANTHROPIC_API_KEY` |
| `google` | Gemini API and Vertex AI | The `google-genai` SDK | Read by the SDK from your environment |
| `bedrock` | Amazon Bedrock | The `boto3` SDK, Converse API | Read by the SDK; `region` option |
| `azure` | Azure OpenAI | The `openai` SDK | Read by the SDK; `endpoint` and `api_version` options |

Casebench does not depend on the three SDKs. Install the one you use in the project; `casebench check` fails the judge with "is not installed here" when it cannot import it. The SDKs read their keys from the environment only, so a key `keys:` reads from a `.env` file does not reach them: set their variables in the shell.

## Pick a model

You pick the provider and the model from a public model catalog, in `casebench init` or on the workbench's Models page. A coding agent or a script reads the same catalog:

```sh
casebench models                  # every provider in the catalog, by id and name
casebench models --json           # the same, with the variable each one's key is read from
casebench models anthropic --json # that provider's models
```

`casebench models PROVIDER` lists that provider's models by id and name. With `--json`, each model comes with its family, its price per million tokens and its context window too. `casebench init --judge-provider ID --judge-model ID` takes the ids as listed. Casebench then picks the built-in provider that speaks that catalog entry's API, by the package the catalog names for it, and fills `base_url`, `api_key_env` and `family` from the catalog, with `max_tokens` where the provider requires one and the model's `context_window`. The catalog's OpenRouter entry, for example, is served by the `openai` provider with OpenRouter's address and `OPENROUTER_API_KEY`.

The Models page shows each model Casebench calls as a card that says what it does: the judge, a second judge from another family, and the two extraction models. Its key can be set and the model tested on the card alone.

## Model settings

Five settings have one name across providers. Nothing is sent unless you set it.

| Setting | `openai`, `azure` | `anthropic` | `google` | `bedrock` |
| --- | --- | --- | --- | --- |
| `reasoning_effort` | `reasoning_effort` | `output_config.effort` | `thinking_config.thinking_level` | in `model_fields` |
| `thinking_budget` | not taken | `thinking: {type: enabled, budget_tokens}` | `thinking_config.thinking_budget` | in `model_fields` |
| `temperature` | `temperature` | not taken | `temperature` | `inferenceConfig.temperature` |
| `max_tokens` | `max_completion_tokens` | `max_tokens`, required | `max_output_tokens` | `inferenceConfig.maxTokens` |
| `model_fields` | not taken | not taken | not taken | `additionalModelRequestFields` |

Bedrock's Converse API carries a model's reasoning settings only as that model's own fields, so give them as `model_fields` and Casebench sends them as they are. A setting a provider does not take is refused when the model is built, naming the ones it takes. Whether a value is valid is for the provider's API to say; `casebench check` shows its answer.

## Family

Each model's family comes from the catalog and is stored as `family`. Casebench uses it to refuse two judges of the same family, and to warn when a judge shares a family with a model listed under `agent_models`. Families are compared as the catalog gives them, never read from a model's name. Without `family`, a provider's own default applies: `openai`, `anthropic`, `gemini`, `bedrock` or `azure`.

## Price

No price is written into `casebench.yaml`. `casebench run`, `import` and `extract` look each model's price up when they start, before the run is held to its hosts:

- a model called through OpenRouter, or named by an OpenRouter id, at OpenRouter's own price, from its public models API;
- any other at the public model catalog's price, found by its id or the id's last segment.

The two requests send nothing of yours. The last lists read are kept in `.casebench/prices.json` and used when a list cannot be read. The workbench prices from that file at once and reads fresh lists in the background. `casebench check` reads no price.

A `price: {input, output}` written in a model's block, in US dollars per million tokens, wins over the lists. Write one for a model no list has, such as one on your own servers. A model with no price gets its tokens counted, and its cost is reported as unknown.

## Another provider

A provider no built-in reaches is a plugin. See [Write a plugin or a profile](/integrations/extend/plugins/).
