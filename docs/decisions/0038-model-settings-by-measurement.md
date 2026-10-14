---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# Each model takes its provider's own settings, and a team picks them from measured agreement, time and cost

Amends [0027](0027-answer-keys-from-decisions.md) (what an extraction records) and [0032](0032-provider-catalog-and-sdk-providers.md) (what `init` takes from the catalog).

## Context and problem statement

Extracting one Turkish decision cost about $0.33 and took 2.5 to 4.5 minutes with two reasoning models (one wrote 28,000 output tokens, the other 10,000), most of it thinking (measured 2026-10-12). Two thousand decisions would cost about $660. Casebench could not pass a reasoning effort, a thinking budget or a temperature to any provider, so nobody could tell whether less thinking gives the same answer keys. The judge has the same gap. `extract` printed nothing when it ran without a terminal, so a run left in the background showed no progress. Rule 3 forbids picking a cheaper setting by guess: the setting has to come from a measurement.

## Considered options

1. Each provider takes the settings its own API documents, under the names Casebench uses everywhere, and passes each in the parameter its vendor documents; `extract` records agreement, time and cost per setting, and `compare` shows two extractions side by side
2. One generic `extra_body` passed through unchanged to every provider
3. Casebench picks a cheaper default effort for extraction

## Decision outcome

Chosen option 1, because a team can then try a setting by name on any provider and decide from numbers, and Casebench never sets a value the user did not.

- **Settings.** A model's `options` in `casebench.yaml` may hold `reasoning_effort`, `thinking_budget`, `temperature` and `max_tokens` (the output limit, as before). None has a default: what is not set is not sent, and the provider's own default applies. Each provider passes a setting in the form its vendor documents, read from the vendor's SDK on 2026-10-14:

  | setting | `openai`, `azure` (openai 3.29.0) | `anthropic` (anthropic 1.13.0) | `google` (google-genai 2.30.1) | `bedrock` (botocore 1.43.113) |
  |---|---|---|---|---|
  | `reasoning_effort` | `reasoning_effort` | `output_config.effort` | `thinking_config.thinking_level` | the model's own field, in `model_fields` |
  | `thinking_budget` | not taken | `thinking: {type: enabled, budget_tokens}` | `thinking_config.thinking_budget` | the model's own field, in `model_fields` |
  | `temperature` | `temperature` | not taken | `temperature` | `inferenceConfig.temperature` |
  | `max_tokens` | `max_completion_tokens` | `max_tokens` | `max_output_tokens` | `inferenceConfig.maxTokens` |

  Bedrock's Converse API carries a model's reasoning settings only as that model's own fields in `additionalModelRequestFields`, so the `bedrock` provider takes them as `model_fields` and sends them as they are. A setting a provider does not take is refused when the model is built, naming the settings it does take; the value is checked by the provider's API, not by Casebench.
- **Check.** `casebench check` sends each model its short question with its settings, and says the settings it was called with when the provider answered, or the provider's refusal when it did not.
- **Price.** `casebench init` takes each model's price per million input and output tokens from the model catalog ([models.dev](https://models.dev) `cost.input`, `cost.output`) into the model's `price`. Without a price, Casebench counts tokens and says the cost is unknown.
- **Measured per setting.** `casebench extract --set NAME=VALUE` sets a setting on both extraction models for one run, over the settings in `casebench.yaml`. Each keys folder's `extraction.json` records each model's settings, the agreement per field, the time per decision and in all, and the tokens and cost of each model. `casebench compare A B`, given two keys folders, shows them side by side.
- **Cost before spending.** `casebench extract --dry-run` sends nothing. It states the decisions, the model calls (two per decision) and a cost range from the prices: at least the input, estimated at four characters per token ([0028](0028-scores-baselines-and-intervals.md)) from the decisions already cached; at most that plus each call's `max_tokens` of output. A model with no `max_tokens` has no upper bound, and the range says so. It is labelled an estimate.
- **Progress without a terminal.** When its output is not a terminal, `extract` prints one line per decision read and `run` one line per case answered and per case scored, each with its time and, where Casebench's own models were called, the running cost.
- **What to measure first.** On the Türkiye corpus, each extraction model's lowest effort and its default, on the same 5 decisions. The measured agreement, time and cost go in this record when that run is made; until then no setting is recommended.

### Consequences

- Good, because a cheaper setting is chosen from its measured agreement, and the keys folder says which setting made its keys.
- Good, because the settings have one name on every provider, and a provider that cannot take one says so before any call.
- Bad, because a vendor that renames a parameter needs a change to its provider; the table names the SDK version each form was read from.
- Bad, because five decisions measure agreement with a wide interval; the comparison shows the counts, not only the rates.

## Revisit when

- The first measurement on the Türkiye corpus is made: its numbers are added here, and the setting it supports is recommended or not.
- A vendor documents a new reasoning parameter, or retires one in the table.

## More information

- OpenAI Python SDK 3.29.0, `types/chat/completion_create_params.py` (`reasoning_effort`, `temperature`, `max_completion_tokens`) and `types/shared/reasoning_effort.py`.
- Anthropic Python SDK 1.13.0, `types/message_create_params.py` (`max_tokens`, `output_config`, `thinking`; no `temperature`), `types/output_config_param.py`, `types/thinking_config_enabled_param.py`.
- google-genai 2.30.1, `types.ThinkingConfig` (`thinking_budget`, `thinking_level`, `include_thoughts`) and `types.GenerateContentConfig` (`temperature`, `max_output_tokens`, `thinking_config`).
- botocore 1.43.113, `bedrock-runtime` `Converse` input (`inferenceConfig`: `maxTokens`, `temperature`, `topP`, `stopSequences`; `additionalModelRequestFields`).
- Extraction measured 2026-10-12: about $0.33 and 2.5 to 4.5 minutes per decision, two reasoning models.
