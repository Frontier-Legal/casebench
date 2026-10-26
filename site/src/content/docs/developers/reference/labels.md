---
title: Labels
description: Every label a score, a citation, an error rate or an authority can carry, and what each one means.
sidebar:
  order: 5
---

A label says why a score is what it is. Every failure in a report carries one, next to its evidence.

## Outcome

The `outcome` metric reads the answer for the outcome labels with no model.

| Label | Means |
| --- | --- |
| `correct` | Exactly one outcome label in the answer, and it matches the court's |
| `wrong outcome` | Exactly one, and it does not match |
| `unreadable outcome` | None, or more than one. An answer the target never gave gets this label too. |

The labels the answer is read for are `upheld`, `reversed`, `partly_reversed`, `remanded`, `granted`, `rejected`, `partly_granted` and `dismissed`. `partly reversed`, `partly-reversed` and `partly_reversed` all read as one label, and `partly reversed` does not also count as `reversed`.

## Statute and precedent

| Label | Means |
| --- | --- |
| `correct` | Every authority the court relied on is cited, and nothing else |
| `missed statute` | Recall below one: a statute the court relied on is not cited |
| `wrong statute` | Precision below one: a cited statute is not one the court relied on, or does not resolve to a corpus document |
| `missed precedent` | The same, for decisions |
| `wrong precedent` | The same, for decisions |
| `reference not resolved` | A court authority of the case has no corpus document, so there is nothing to compare against |

A score with both problems carries both, such as `missed statute, wrong statute`. A citation no connected corpus could look for is left out, not counted as wrong.

## Research authorities

The `authority_recall` and `authority_ndcg` metrics compare the answer's first ten authorities, in order, with the case's key authorities.

| Label | Means |
| --- | --- |
| `all key authorities found` | Every key authority is among the answer's first ten |
| `missed key authority: ...` | The key authorities that are not, by the value the case gives them, separated by `; ` |
| `reference not resolved` | A key authority has no corpus document yet. `casebench case resolve` resolves them. |

## Criteria

| Label | Means |
| --- | --- |
| `all criteria passed` | Every positive criterion met, no negative one triggered |
| `failed: c-statute-1, c-answer-1` | The criteria that did not pass, by id |

A verdict of met stands only on a quote the answer holds word for word. When the judge finds a criterion met and quotes nothing the answer says, the verdict counts as not met, and its note reads "the judge found it met but quoted nothing the answer says, so it does not count". With two judges, a criterion passes only when both pass it.

## Editing

| Metric | Label | Means |
| --- | --- | --- |
| `issues_found` | `all issues found` | The edit changed the clause of every issue the case lists |
| `issues_found` | `missed issues: 4: ...` | The issues whose clause the edit left unchanged, by clause number and issue, separated by `; ` |
| `edit_preservation` | `preserved` | No clause outside the issues changed |
| `edit_preservation` | `changed outside the edit: 2, 7` | The clauses outside the issues that changed |
| `edit_preservation` | `no clause outside the issues` | Every clause is an issue, so there is nothing to preserve |

## Extraction

| Label | Means |
| --- | --- |
| `all fields matched` | Every expected field matched |
| `wrong fields: party, date` | The fields that did not match |
| `no JSON object of fields` | The answer is not a JSON object, or the target gave none |

## No output

| Label | Means |
| --- | --- |
| `no output` | The target returned nothing for this case, or failed on it |

`citation_integrity`, `criteria`, the statute, precedent and research metrics, `issues_found` and `edit_preservation` use it. `outcome` labels a missing answer `unreadable outcome`, and `fields` labels it `no JSON object of fields`.

## Citations

A `citation_integrity` score is labelled with its counts, such as `3 verified, 1 fabricated`, or `cites nothing` for an answer with no citation. Each citation carries one of:

| Label | Means | Counts against the answer |
| --- | --- | --- |
| `verified` | The document exists and supports the claim | No |
| `misgrounded` | The document exists and does not support the claim | Yes |
| `fabricated` | A corpus that could hold it was searched and holds no such document | Yes |
| `unchecked` | No connected corpus covers the citation's jurisdiction or kind | No |

The score is the share of checked citations that are verified. An answer whose citations could none of them be checked scores 1. With two judges, a citation is verified only when both verify it.

## Error rates

A report gives four error rates, each the share of answers the error could occur in, with its interval and the answers that have it. An error no answer in the run could have is left out.

| Error | Means | Counted over |
| --- | --- | --- |
| `fabricated citation` | Cites a decision or statute the corpus does not hold | Answers scored for `citation_integrity` |
| `unsupported claim` | Cites an authority the corpus holds for something it does not say | Answers scored for `citation_integrity` |
| `wrong outcome` | Does not reach the ruling the court or the lawyer gave: states another, or none | Answers scored for `outcome`, or graded on a criterion of the `outcome` kind |
| `wrong statute` | Relies on a statute the court did not apply | Answers scored for `statute` |

`casebench report RUN_DIR` computes them again with each lawyer's latest verdict in place of the judge's.

## Unevidenced

A case is unevidenced when a metric it names has nothing to earn in it. The metric does not score it, which is no scoring error, and the report lists the case under `unevidenced`. A run prints a line such as `unevidenced: 2 cases have no evidenced fact for a metric they name, which did not score them: ...`.

| Metric | Has something to earn when |
| --- | --- |
| `criteria` | At least one criterion has a positive weight |
| `authority_recall`, `authority_ndcg` | The case has key authorities, each resolved to a corpus document |
| `issues_found`, `edit_preservation` | The case lists at least one issue |
| `fields` | The case has at least one expected field |

## Authority funnel

| Label | The court's authority |
| --- | --- |
| `retrieval_miss` | Was never returned by a retrieval, rerank or document step |
| `rerank_drop` | Was retrieved and dropped by a rerank |
| `not_in_context` | Never appeared in a model call's request |
| `ignored_authority` | Reached the model and was not cited |

A citation that resolves to a document no step returned is `ungrounded`: the model wrote it from memory. A step with no document ids carries the note "no diagnostic possible".

## Approval

| Value | Shown as | Means |
| --- | --- | --- |
| `approved` | `lawyer-approved` | A lawyer approved the reference |
| `draft` | `unreviewed` | Not yet approved. It can be run, and is reported apart. |

## Reference source

| Value | The reference came from |
| --- | --- |
| `court` | A court decision, through extraction or a lawyer's pick |
| `lawyer` | A lawyer, written by hand |
| `structured` | Expected fields |
| `hybrid` | A lawyer's answer with corpus-verified authorities |
