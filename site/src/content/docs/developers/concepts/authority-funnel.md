---
title: The authority funnel
description: Follow each authority the court relied on through your agent's steps, retrieved, kept, read, cited, to see where the right one was lost, with no model assigning blame.
sidebar:
  order: 4
---

A wrong answer says nothing about why. With a court reference, Casebench knows the authorities the court relied on, so it can follow each one through the steps your agent took and find the first step that lost it. Every stage is a lookup by document id that anyone can repeat from the run folder.

## The stages

| Stage | Passed when | Failure label |
| --- | --- | --- |
| Retrieved | A retrieval, rerank or document step returned its id | `retrieval_miss` |
| Kept | A rerank step returned it. Checked only when a rerank was captured. | `rerank_drop` |
| Read | Its id appears, as a whole word, in the request of a model call | `not_in_context` |
| Cited | The answer cites it, resolved by the judge and the corpus | `ignored_authority` |

The first stage an authority fails gives its label. Whether the cited passage supports the claim is the citation check's job, and is not repeated here.

A citation in the answer that resolves to a corpus document no step returned is `ungrounded`: written from the model's memory, right or wrong.

## Reading it

```text frame="terminal"
authority funnel: 287 court authorities in 112 cases with captured document ids (8 cases had none)
  retrieved    241    84%
  kept         203    71%
  read         151    53%
  cited        118    41%
  ignored_authority 33, not_in_context 52, rerank_drop 38, retrieval_miss 46
  ungrounded citations: 9
  read means the document's id was in a model call's request
```

These figures are illustrative. Here the retriever found the right decision 84% of the time, but only 53% reached the model's context. That is a rerank or context-budget problem, not a model problem, and changing the model would not fix it.

## What "read" means

An agent that puts a document's text in the prompt without its id shows as `not_in_context`. The label says the id was missing, and the report says how read was decided. If your agent strips ids, include them in the context, or record the step with a function in the config that returns them.

## When it cannot say

- A case whose steps carry no document ids gets "no diagnostic possible", and the funnel counts only cases with ids. With none at all, it prints that instead of a number.
- Without a judge, the funnel stops at "read" and says so.
- The funnel never changes a score. It explains one.

## Per answer, in the workbench

The engineering view of an answer shows the same funnel beside the answer's steps: for each of the court's authorities, the step that retrieved it, the rerank that kept it, the model call that read it, and whether the answer cited it and characterised it correctly. Picking another run of the same suite shows each authority's funnel in both runs, so a step that stopped retrieving it stands out.

## Why not ask a model which step failed

Research on multi-step agents found that the best judge-based method identified the failing step about 14% of the time ([Who&When](https://arxiv.org/abs/2505.00212)). Following document ids is slower to set up and right every time.

## Related

- [Record retrieval steps](/developers/guides/capture/retrieval-steps/).
- [A retrieval agent with the funnel](/examples/walkthroughs/retrieval-funnel/).
