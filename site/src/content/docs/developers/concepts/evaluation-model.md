---
title: The evaluation model
description: Cases, tasks, references and metrics, the three axes Casebench never blends, and why a criterion cannot exist without evidence.
sidebar:
  order: 1
---

The unit of Casebench is an evaluation case, not a court decision. A case is a task the AI performs, a reference to grade it against, and the metrics to apply. Court decisions are one way to build references. Lawyers are another.

## A case

```yaml
id: employment-7
task:
  type: qa
  question: Can an employer dismiss an employee for a single late arrival without a prior written warning?
reference:
  source: lawyer
  author: Ayşe Demir
  facts:
    - id: answer-1
      kind: answer
      value: No. A dismissal for one late arrival with no prior warning is disproportionate.
      evidence: { doc: reviewer, note: written by Ayşe Demir }
    - id: statute-1
      kind: statute
      value: Employment Act s. 18
      evidence: { doc: reviewer, note: written by Ayşe Demir }
  criteria:
    - id: c-answer-1
      text: "Passes if the answer reaches this conclusion: No. ... Fails if it reaches another conclusion or none."
      weight: 1
      from: [answer-1]
metrics: [criteria, citation_integrity]
approval: approved
```

## Three axes, never blended

| Axis | Values | Where it comes from |
| --- | --- | --- |
| Task type | `qa`, `research`, `drafting`, `editing`, `extraction`, `outcome`, and the court test types `statute` and `precedent`, plus plugins | What the AI is asked to do and what its output looks like |
| Reference source | `court`, `lawyer`, `structured`, `hybrid` | Recorded on every fact |
| Metric | `outcome`, `statute`, `precedent`, `criteria`, `citation_integrity`, `authority_recall`, `authority_ndcg`, `issues_found`, `edit_preservation`, `fields` | Listed on the case; each task type has defaults |

Each task type has default metrics: `qa` is graded by `criteria`; `research` by `authority_recall`, `authority_ndcg` and `citation_integrity`; `drafting` by `criteria` and `citation_integrity`; `editing` by `issues_found` and `edit_preservation`; `extraction` by `fields`; `outcome` by `outcome`. See [Research, drafting, editing and extraction](/developers/guides/suites/other-tasks/).

Any combination is allowed. The report has one table per task and metric, with a row per reference source, approval state and jurisdiction, and gives each figure by practice area. It never averages them into one number, because a court-derived outcome score and a lawyer-graded drafting score answer different questions, and an average of the two answers neither.

## A reference has two layers

- **Facts**, each tied to evidence: a passage in a decision (a quote, located by its span), a lawyer's note, or a corpus document id.
- **Criteria**, derived from those facts, each a pass or fail check with a signed integer weight.

A criterion with a positive weight must name the facts it comes from. A model never writes the rubric it then grades against. A lawyer writes key points, in the workbench or a spreadsheet, as weighted lines such as `+3 Says the reduction needs written consent.`; each becomes a criterion that comes from the lawyer's reference answer. For a case drawn from a court decision, or written with `casebench case new`, Casebench words one criterion per fact in a fixed form, such as "Passes if the answer relies on Employment Act s. 18. Fails if it does not." A case with no criterion of positive weight has nothing to earn: it is reported as unevidenced and not scored for criteria.

A criterion's score is the sum of the weights of the criteria met, over the sum of the positive weights, clipped to between 0 and 1. A negative weight is a penalty: "Fails if the answer cites a repealed provision."

## Approval

Every case is `draft` or `approved`, and an approved case names who approved it. Court-derived cases start as drafts, and you can run them at once; a lawyer approves them fact by fact in the workbench. The report keeps lawyer-approved and unreviewed rows apart, so an unreviewed answer key never passes for an approved one. A case may also name its practice area, and every figure is given per practice area.

## Suites and runs

A suite is a folder: `suite.jsonl` with one case per line, and `manifest.json` with the suite's id, a SHA-256 content hash over the cases in order, the Casebench version that froze it, and the mix of task types, sources and approvals. Any change to any case changes the hash.

A run is a folder too: every output, captured step, score and error of one suite against one target, appended as it happens. A run can be scored again without calling the target. See [Run folder](/developers/reference/run-folder/).

## No country-specific code

Casebench has no parser, word list or citation format for any country. Models read decisions and answers, and your corpus resolves citations whatever their format. A new jurisdiction costs a connector to its documents, not code in Casebench.

## Related

- [Court-derived references](/developers/concepts/court-references/).
- [Case format](/developers/reference/formats/case/), every field.
