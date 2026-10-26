---
title: How Casebench grades an answer
description: Where the answer key comes from, what the grading model is allowed to decide, and why your verdict always wins.
sidebar:
  order: 1
---

Every grade in Casebench rests on evidence a lawyer would accept: a court decision, or a lawyer's own judgment. A model helps read and compare. It never invents what the right answer is.

## The answer key comes from evidence

There are two sources.

**A court decision.** A decided case already contains its answer: the ruling, the provisions applied, the decisions relied on. Casebench has two different AI models read each decision separately. The outcome becomes part of the answer key only where both name the same one, and the statutes or precedents only where both quoted the same passages for them. Where they disagree, that part is left out rather than guessed.

**A lawyer.** You write the question, the expected answer and the authorities yourself. Your words are the key.

Either way, every point in the key is tied to its evidence: the passage in the decision, or a note that you wrote it.

## Checks, not impressions

Every point of the answer key is a pass-or-fail check with a weight. You write them yourself as key points, such as `+3 Says the reduction needs written consent.` For a case drawn from a court decision, Casebench words each check from the approved fact, such as "Passes if the answer relies on section 98. Fails if it does not." There are no 1-to-5 ratings and no "mostly correct". A check is met or it is not.

Some checks need no model at all. Whether the AI named the right outcome of a decided case is a matter of reading one word, and Casebench does it exactly.

## What the grading model does

For checks that need reading, Casebench uses a grading model, called the judge, chosen by your team and run on your team's account. The judge:

- reads the AI's answer and decides each check, quoting the passage of the answer that decides it. A finding that the answer makes a point, with a quote the answer does not hold, counts as the point not made;
- lists every citation in the answer and the claim each one supports;
- decides which document in your source a citation refers to, and whether that document supports the claim.

## What it is not allowed to do

- **Decide what exists.** Whether an authority exists is decided by your source of decisions and statutes, never by a model's memory.
- **Ask the AI under test.** The system being graded is never asked to confirm its own citations.
- **Write the checks.** Checks come only from the answer key.
- **Overrule you.** Your verdict on any check replaces the judge's, in every report, chart and check your engineers run.

## When two judges disagree

Your team can require a second judge from a different model family. A check or citation then passes only when both judges pass it, and every disagreement is listed for a lawyer to decide. Until a lawyer decides, a disagreement counts as failed.

## Related

- [What a citation verdict means](/lawyers/concepts/citation-verdicts/).
- [Answer keys from court decisions](/lawyers/concepts/court-answer-keys/).
