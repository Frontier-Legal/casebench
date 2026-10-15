---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# A verdict rests on a quote the answer holds and on the case's evidence, and lawyers' verdicts calibrate the judge

Amends [0002](0002-evaluation-case-model.md) (what a criterion verdict holds), [0029](0029-statute-and-precedent-scores.md) (the warning about a judge of the target's family) and [0035](0035-comparable-and-strict-scores.md) (judge agreement). Raises the report format to 1.1 ([0034](0034-versioned-formats.md)).

## Context and problem statement

A criterion is written by Casebench from an evidenced fact, never by a model (0002), and the judge is asked to quote the passage of the answer that decides it. Four things were still taken on trust:

- **The quote.** Nothing checked that the judge's quote is in the answer, so a judge could find a criterion met with a quote it made up. The verdict did not say what evidence the criterion rests on.
- **Cases with no facts.** A case naming the `criteria` metric with no evidenced fact had no criterion to earn. Scoring it failed, and it was then scored again on every run.
- **The family warning.** `casebench run` warned on every run that a judge of the target's family favours it, without checking. `init` already reads the families of the agent's models from the catalog, then forgot them.
- **Lawyers.** Two judges' agreement was measured (0035), but agreeing models are not evidence that either is right. A lawyer had no way to record a verdict on the judge's.

## Considered options

1. Check each quote against the answer; record the families of the agent's models in `casebench.yaml` and compare; let a lawyer record a verdict per criterion in the run's folder, and count it against the judge's.
2. As 1, but let a lawyer's verdict replace the judge's in the scores.
3. Leave verdicts as they are until the review workbench exists.

## Decision outcome

Chosen option 1. Option 2 mixes two sources into one figure, which reports never do (rule 8); a lawyer's verdict is reported beside the judge's. Option 3 leaves scores resting on quotes nobody checked.

- **A verdict's quote is in the answer.** A judge that finds a criterion met must quote the answer. The quote is compared with the answer after Unicode normalisation (NFC) and with runs of whitespace taken as one space. A verdict of met with no quote, or with a quote the answer does not hold, counts as not met, and its note says why. With two judges each verdict is checked before they are combined.
- **A verdict names its evidence.** Each verdict carries the evidence of the facts its criterion comes from: the court's passage, or the value the lawyer wrote. The judge receives that same evidence: a lawyer's fact, which has no passage, is sent with its value and the lawyer's note.
- **Unevidenced cases.** A case that names `criteria` but has no criterion with a positive weight has nothing to earn. It is not scored for criteria and is not a scoring error. The report lists it as unevidenced, and `casebench case new` says so when it writes one.
- **The agent's families.** `casebench.yaml` gains `agent_models:`, each model the agent calls, with its family from the model catalog. `init` writes the models it finds in the code, and the guide has the coding agent do the same with `casebench models`.
  - At the end of a run, each judge whose family matches one of the agent's models gets a warning in the report and on the terminal.
  - With no `agent_models:`, the warning says the agent's family is not known, so it was not checked.
  - A model the agent called during the run that `agent_models:` does not list is named, since the check could not cover it.
  - The family comparison is exact, between catalog families; nothing is inferred from a model's name.
- **Lawyers' verdicts.** `casebench review criterion RUN --case ID --criterion ID --verdict pass|fail --by NAME` records a lawyer's verdict in the run's folder, `reviews.jsonl`, one line each, scrubbed of keys like every line a run writes.
  - A verdict that overrules the judge's needs `--note`, saying why.
  - The report's calibration counts, for each kind of criterion (the kind of fact it comes from: outcome, answer, statute, precedent), the verdicts lawyers gave, how many agreed with the judge, and how many overruled it, against the score set the report shows.
  - Scores stay the judge's.
- **The report format is 1.1.** It adds `warnings`, `unevidenced` and `calibration`, and each criterion verdict gains `evidence` and `note`. All are optional, so a 1.0 report stays valid.

### Consequences

- Good, because a met criterion always points at words the answer holds, and at the evidence it was measured against.
- Good, because the judge is measured against lawyers on the same run, per kind of criterion, before anyone relies on it.
- Bad, because a judge that paraphrases instead of quoting loses criteria it found met. The note says so, and the prompt already asks for an exact copy.
- Bad, because `agent_models:` must be kept up to date when the agent changes models. The run names any model it saw the agent call that the list leaves out.

## Revisit when

- Judges paraphrase often enough that exact quotes cost many true verdicts.
- The review workbench (R1) records lawyers' verdicts; it writes the same `reviews.jsonl`.

## More information

- [0002](0002-evaluation-case-model.md), [0035](0035-comparable-and-strict-scores.md), [0032](0032-provider-catalog-and-sdk-providers.md) (families from the catalog).
