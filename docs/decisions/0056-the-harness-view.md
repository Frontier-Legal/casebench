---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Engineers see each answer as a waterfall of its calls, with unaccounted time, the authority funnel and a diff against another run

Adds to [0050](0050-the-review-queue.md) (two views), [0051](0051-what-a-run-spends.md) (what a run spends) and the authority funnel ([harness-eval.md](../design/harness-eval.md)). Follows the workbench design ([workbench.md](../design/workbench.md), "Harness view").

## Context and problem statement

A run records each answer's steps: every model call, tool call, retrieval and rerank, with its start and end, model, tokens and the document ids that went in and out. Capture also records time no step covers as a gap step. The engineering view lists these steps as a table. An engineer cannot see which of twelve calls was slow, where time went unrecorded, which step lost the court's authority, or what changed for one case between two versions of the agent.

## Considered options

1. A harness view in the workbench's engineering view, computed from the run folder when an answer is opened. It shows a waterfall, sums per step and per model, the funnel with the step at which each authority reached each stage, and a diff against the same case in another run of the suite.
2. Export the steps as OpenTelemetry spans and let a tracing tool draw them.
3. Add the waterfall to the terminal report.

## Decision outcome

Chosen option 1, because the run folder already holds everything the view needs, and the funnel and the diff need the case's gold authorities and the other run, which no tracing tool holds. Option 2 adds a second tool to understand one eval result ([workbench.md](../design/workbench.md)). Option 3 cannot draw time.

- **Where.** An answer opened in the engineering view shows the harness view below its engineering card. The API serves it only to the engineering view. Under `casebench ui --role reviewer`, and in the review view, it is refused and not offered ([0050](0050-the-review-queue.md)).
- **The waterfall.**
  - Each step is a bar in start order, placed by its start and drawn to its length from the answer's first start. Beside it are its kind, name, model, duration, input and output tokens and cost; a tool call also shows its arguments, cut short.
  - A step without times is listed after the bars in recorded order, and the view says so.
- **Gaps are shown, not hidden.**
  - Time between steps that no step covers is a bar of its own, labelled unaccounted, with its length. Capture's gap steps are used as recorded; for steps captured without them, gaps are found the same way.
  - When the answer's latency is longer than the span from the first start to the last end, the difference is shown as unaccounted time outside the steps.
- **Sums.** One table per step name and one per model: calls, input and output tokens, cost and time.
- **Cost is an estimate.** It is computed per model call from the price `casebench.yaml` gives the agent's model ([0051](0051-what-a-run-spends.md)), which `init` writes from the provider's published prices. The view labels it an estimate, and a call whose model has no price shows none.
- **The funnel beside the calls.** For each gold authority of the case, the view gives the step at which it was retrieved, kept by a rerank, and read by a model call, and whether the answer cited it and characterised it correctly.
  - Cited and characterised come from the citation checks the run was scored with: a citation the judge resolved to the document, and labelled verified or misgrounded. The view calls no model.
  - A stage that cannot be checked shows "not checked": there is no rerank step, or no citation check.
  - With no document ids in any step, the view says no funnel is possible, as the report does.
- **The diff against another run.**
  - The engineer picks another run of the same suite that answered the case. Steps are matched by kind, name and model, in order of occurrence.
  - Each matched step shows its time and tokens in both runs. A step at least 10% and 50 ms slower is marked slower; one using at least 10% more tokens is marked as using more. A step only in the earlier run is marked gone, and one only in the later run new.
  - Each authority's funnel is shown for both runs, so a step that stopped retrieving it stands out.

### Consequences

- Good, because a slow call, a missing span and a lost authority are each one look away from the answer they explain.
- Good, because nothing new is captured or stored: the view reads the run folder.
- Bad, because matching steps by kind, name and model pairs the wrong calls when a run reorders identical calls.
- Bad, because an estimate from the configured price can differ from the provider's bill.

## Revisit when

- Steps carry stable ids across runs, so the diff can match them exactly.
- Teams ask for the waterfall across all cases of a run.

## More information

- The authority funnel: [harness-eval.md](../design/harness-eval.md).
