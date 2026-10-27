---
title: Citation checks
description: How Casebench decides whether a citation exists and says what the answer claims, with the judge reading and the corpus deciding what exists.
sidebar:
  order: 3
---

A citation can exist and still not say what the answer claims. Checking it takes three things only a reader can do, and one thing only the corpus can do:

1. **List.** The judge reads the answer and returns every citation exactly as written, with the claim the answer makes about it, its jurisdiction where the citation shows it, and whether it cites a statute or a decision.
2. **Find.** The corpus searches for the citation and returns its first `candidates` results, five by default.
3. **Match.** The judge sees the citation and each candidate's court, date, metadata and the passage that best matches the citation's words, or the description the search result gives, and names the one the citation refers to, or none.
4. **Weigh.** For a matched document, the judge reads its text and decides whether it supports the claim, quoting the passage.

Each step sees only what it needs. The corpus decides what exists.

## The labels

| Label | Means |
| --- | --- |
| `verified` | The document exists and supports the claim. The judge's quote is kept. |
| `misgrounded` | The document exists and does not support the claim. |
| `fabricated` | A corpus that covers the citation's jurisdiction was searched and holds no such document. |
| `unchecked` | No connected corpus covers the citation's jurisdiction or kind. Never counted against the answer. |

The `citation_integrity` metric scores an answer as the share of its checked citations that are verified. Unchecked citations are left out of that share, and an answer with no checked citation scores 1. Every citation's label and quote stay on the score, and the report counts each label across the run.

## The grader never asks the system it grades

Citation checks read your corpus, never the AI under test. A config whose corpus is the target is refused before anything is sent. A corpus that is the same document API the agent retrieves from is fine: the agent may retrieve from it, but it cannot vouch for itself.

## The judge can be wrong

The judge is a model, and it runs on your key, never on the system under test. Casebench limits what it decides and checks it:

- It decides which document a citation means and whether a passage supports a claim. It never decides whether a document exists.
- A second judge from another model family can be required to agree. A citation is verified only when both verify it, and every disagreement is listed for a lawyer.
- Lawyers read each citation's verdict beside its source passage in the workbench's review queue. Their verdicts are given on criteria, the points an answer must make, and replace the judge's there; a citation's label itself is not overruled.
- Every judge reply is kept in the run's `judge.jsonl`, keyed by provider, model and prompt, so a re-score gives the same answer at no cost.

## Cost

Each answer costs judge calls: one to list its citations, then as few matching calls as the judge's context window allows for all of them together, then one weighing call per matched citation. The dry run counts them before you spend.

## Related

- [Citation labels](/developers/reference/labels/).
- [Choose the judge](/developers/guides/connect/judge/).
- For lawyers: [What a citation verdict means](/lawyers/concepts/citation-verdicts/).
