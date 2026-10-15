---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# A run reports what it spent, per model, for the agent and for the judge

Adds to [0038](0038-model-settings-by-measurement.md) (model settings and prices) and [0047](0047-the-judge-rests-on-evidence.md) (the agent's models).

## Context and problem statement

A run calls two kinds of model: the agent's, while it answers, and the judge's, while it grades. Today a run prints the judge's cost while it scores, from the price `casebench.yaml` gives the judge ([0038](0038-model-settings-by-measurement.md)), and then forgets it. The agent's calls are recorded as steps with their tokens, but nothing prices them. So a team cannot say what a run cost, what share went to grading, or which model drove it. The workbench cannot hold its "try a question" to a budget in dollars either.

## Considered options

1. Price every model call the run records, the agent's from its steps and the judge's from its kept replies, at the prices in `casebench.yaml`, and report the spend per model.
2. Report tokens only, and let each team price them.
3. Ask each provider's billing interface.

## Decision outcome

Chosen option 1, because the run already records every call with its model and tokens, and the catalog gives prices. Option 2 leaves every team doing the same sum. Option 3 needs billing access Casebench must never hold, and it cannot tell one run's calls from another's.

- **Prices.**
  - Each model in `agent_models` takes a `price`, in US dollars per million input and output tokens, as the judge's does. `casebench init` writes it from the model catalog, and the guide has the coding agent write it.
  - A price is the team's own figure, which they may change, for example to a negotiated rate.
- **The agent's spend** comes from each result's steps: every model call the run recorded, with its model and tokens.
  - A step's model is matched to an entry in `agent_models` by its id, by its last path segment, or as a dated version of it, such as `model-2026-01-01` for `model`.
- **The judge's spend.** Each judge call that is not answered from the kept replies writes its model and tokens beside its reply in `judge.jsonl`. The spend is the sum over those lines.
  - Scoring a run again asks the judge nothing new, so it adds nothing.
  - Replies kept before this change carry no tokens and are counted as calls without tokens.
- **The report.** `report.json` gains `spend`: one line per model, saying whose it is (the agent's or the judge's), its calls, its tokens and its cost, then the agent's total, the judge's total, the run's total, and the models that have no price.
  - A model without a price is reported with its tokens and no cost. It is named as unpriced, never counted as free.
  - The terminal report prints the same after the tables.
  - Report format 1.1, not released yet, carries it.
- **The workbench** shows what each answer cost the agent, in the engineering view.
- **Only model calls are counted.** Search APIs and other services the agent pays for are not; the report says so.

### Consequences

- Good, because every run says what it cost and where the money went, with the judge's share apart.
- Good, because the workbench can hold a daily budget in dollars on the same sums.
- Bad, because a price is only as current as the catalog was when it was written, or as the team keeps it.
- Bad, because a provider that reports no tokens for a call leaves that call uncounted; it is counted as a call.

## Revisit when

- Teams want the agent's other paid services counted.
- Providers start reporting the cost of each call themselves.

## More information

- Prices come from the model catalog Casebench reads for families and context windows ([0032](0032-provider-catalog-and-sdk-providers.md)).
