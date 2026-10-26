---
title: What a citation verdict means
description: Verified, misgrounded, fabricated and unchecked, what each verdict means for a citation, and how Casebench reaches it.
sidebar:
  order: 2
---

When a case is graded on its citations, Casebench checks every citation in the answer, not only the ones that look wrong. Each citation gets one of four verdicts. Cases drawn from court decisions are graded this way; for a case written in Golden data, your engineer decides whether its citations are checked.

| Verdict | In plain words | Counts against the AI |
| --- | --- | --- |
| **verified** (green) | The authority exists and says what the answer claims | No |
| **misgrounded** (orange, "Misused") | The authority exists but does not say what the answer claims | Yes |
| **fabricated** (red, "Not found") | No such authority exists in a source that covers that jurisdiction | Yes |
| **unchecked** | No connected source covers that jurisdiction, so Casebench cannot say | No |

## Misgrounded is the dangerous one

A fabricated citation fails the first time anyone looks it up. A misgrounded one survives a quick check: the decision is real, the citation is formatted correctly, and only a reader who opens it finds that it was decided on another point, or held the opposite. That is the error most likely to reach a client, and Casebench counts it separately so it is not hidden among the verified ones.

## How a verdict is reached

1. The grading model reads the answer and lists each citation exactly as written, with the claim the answer makes about it.
2. Your source of decisions is searched for that citation.
3. The grading model looks at the results and names the document the citation refers to, or none.
4. If it named one, it reads the document and decides whether it supports the claim, quoting the passage that does.

If the search found nothing the citation could mean, in a source that covers that jurisdiction, the citation is **fabricated**. If a document was found and supports the claim, **verified**, and the supporting passage is kept so you can read it. If found and not supporting, **misgrounded**.

## When you disagree

In the review queue you give verdicts on the points an answer must make, not on citations. Each citation's verdict is shown with its source passage so you can read it, but it cannot be overruled there. When you think a citation verdict is wrong, overrule the point it affects, say why in the note, and tell your engineer. See [Review an answer](/lawyers/guides/review-an-answer/).

## What a verdict does not say

- "Verified" means the document supports the claim the answer made. It does not mean the claim is the best argument, or that the authority is still good law on a later date.
- "Fabricated" means not found in your connected source. If your source is incomplete, a real authority it lacks will look fabricated. Your engineer can check what the source covers.
