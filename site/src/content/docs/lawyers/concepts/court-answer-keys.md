---
title: Answer keys from court decisions
description: Why a decided case is already a test with its answer, how Casebench reads it out safely, and what court records cannot test.
sidebar:
  order: 5
---

A decided case is already a test with its answer. The court was asked a question; the operative part says how it ruled; the reasoning names the provisions and decisions it relied on; the date fixes which version of the law applied. A judge wrote all of it.

Casebench uses this. From decisions your firm already holds, it builds tests at the cost of some computing, instead of hours of lawyer time.

## What becomes a test

| Test | The AI is given | Correct when |
| --- | --- | --- |
| Outcome | The facts, with the ruling removed, and "How did the court rule?" | It names the same outcome as the court |
| Statutes | The facts, and "Which statutes and articles decide this dispute?" | It relies on the provisions the court relied on |
| Precedents | The facts, and "Which earlier court decisions does this dispute turn on?" | It relies on the decisions the court relied on |

The answer is what the court decided, never a model's opinion. The facts are written by one of the two models from the decision, without the ruling, and the question is a fixed one for each kind of test. That is why a lawyer checks each draft before it counts.

## How the key is kept honest

- **Two readers must agree.** Two different AI models read each decision. The outcome counts only where both name the same one. The statutes, or the precedents, count only where every one of them is backed by a passage both models quoted; one disagreement drops that whole list for the decision, rather than guessing. The report states how often they agreed.
- **Every point has its passage.** You can always see where in the decision a point came from.
- **Unreviewed is labelled.** Until a lawyer approves a case, its results appear in their own row, marked unreviewed.
- **Recent decisions only, if needed.** Tests can be built only from decisions published after the AI's training cutoff, so it cannot answer from memory.

## What court records cannot test

Drafting, editing and advice have no ruling to compare against. A contract clause has no court-given right answer. For those, a lawyer writes the case. Casebench reports what court records prove, and says what they do not.
