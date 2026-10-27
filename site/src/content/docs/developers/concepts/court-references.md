---
title: Court-derived references
description: Why a court decision is already a labelled example, how two models read the labels out, and what keeps a wrong answer key out of a suite.
sidebar:
  order: 2
---

A court decision is already a labelled example. Its operative part is the right outcome. Its citations are the authorities the court relied on. Its date fixes which version of a statute applied. A judge wrote all of it, and your team already holds it.

Casebench reads those labels out of your decisions, so an answer key costs extraction compute instead of lawyer hours. No model writes the answer: it is what the court ruled, and every fact points at a passage in the decision. The question is a fixed one per test type, and the facts given with it are written by the first extraction model without the ruling, which is why a lawyer approves each draft.

## Two models, agreement by passage

A model can misread a decision, and a wrong answer key is worse than none: it marks a correct agent wrong. So two different models read each decision independently. For each one, a model returns:

- the outcome, as one label from a shared vocabulary: `upheld`, `reversed`, `partly_reversed`, `remanded`, `granted`, `rejected`, `partly_granted`, `dismissed`, with a quote;
- each statute and each decision the court relied on, as written, with a quote;
- the facts written out without the ruling.

Casebench finds each quote in the decision's text and records its span. An item whose quote is not in the text has no evidence and is dropped.

Agreement is decided per field, by where the quotes point, not by comparing strings:

| Field | Agreed when |
| --- | --- |
| Outcome | Both labels are equal |
| Statutes, precedents | Every item of each model overlaps the span of an item of the other, both ways |

Two quotes from the same place are the same evidence whatever language or citation format the decision uses. Two strings can differ in spelling and still mean one statute. A field the models disagree on gets no key for that decision.

The facts are written by the first model and kept only if they quote neither the outcome passage nor its label. They are the question, not a key.

## From keys to cases

`casebench generate` builds cases by type from the agreed keys:

| Type | The agent gets | Scored by |
| --- | --- | --- |
| `outcome` | The facts, without the ruling | Exact match on the outcome label. No model is called. |
| `statute` | The facts and the legal question | Precision and recall of the cited statute documents against the court's |
| `precedent` | The facts and the legal question | The same, over decisions |

Statute and precedent keys are resolved to corpus documents once, when the suite is generated, and frozen with it. A citation the corpus does not hold is dropped, and the manifest counts what was dropped.

## What keeps a key honest

| Risk | Control |
| --- | --- |
| A wrong answer key | Two models must agree; a disagreement excludes the field. The agreement rate is reported per field. |
| An unreviewed key passing for approved | Every case carries its approval state, and the report keeps the rows apart. |
| The model memorised the decision | `--after` keeps only decisions after the model's training cutoff. |
| The question gives the answer away | Majority-class and text-only baselines beside every outcome score. |

## What court records cannot label

Drafting, editing and advice have no ruling to compare against. For those, a lawyer writes the reference. Casebench says what court records can prove and names what they cannot.

## Related

- [Build a suite from court decisions](/developers/tutorials/court-suite/).
- [Choose extraction settings by measurement](/developers/guides/suites/extraction-settings/).
