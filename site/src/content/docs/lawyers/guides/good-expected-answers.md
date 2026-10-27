---
title: Write a good answer key
description: How to word a question, a reference answer and weighted key points so the grading is fair to the AI and tells you something.
sidebar:
  order: 8
---

A case is only as good as what it asks and what it expects. The AI is graded on your key points, one by one, so most of the care goes there.

## The question

- **One legal question per case.** "Is the dismissal valid, and what compensation is due?" is two cases. A partial answer to a double question cannot be graded cleanly.
- **Ask it the way the AI's users ask.** For a research assistant used by your lawyers, put the point of law as a lawyer would: "Under Examplia law, is unused annual leave forfeited at the end of the leave year if the employer never invited the employee to take it?" For a service clients use directly, use the client's own words.
- **Give the facts the answer depends on.** If the outcome turns on whether a warning was in writing, say whether it was.
- **Name the jurisdiction and the date when they matter.** "Under the law in force in March 2024" saves the AI from guessing which version applies.

## The reference answer

Write the answer you would give, conclusion first: "No." or "Yes, if the notice was served in writing." The grading model reads it as your evidence when it decides each key point, so it should state the law the points rest on.

## The key points

Each line is one point, with its weight first:

```text
+3 Says the reduction needs the employee's written consent.
+1 Treats pay as an essential term of the contract.
-3 Says the employer may reduce pay unilaterally.
```

- **One checkable point per line.** "Correct analysis of consent" cannot be checked; "Says the reduction needs written consent" can.
- **Weigh what decides the question.** The conclusion and the rule it rests on carry the most. A point a good answer could leave out should weigh little, or not be a point at all.
- **Use negative weights for errors that matter.** A wrong limitation period, a repealed article, an outcome the court rejected. An answer loses the weight when it makes the error.
- **A line without a weight weighs 1.**

The report also gives **all passed**: the share of answers that earned every positive point and made none of the errors. An answer that misses the decisive point is wrong, however many small points it earns, and that figure counts it so.

## Statutes and precedents

- **List the authorities the answer rests on**, one per line, as you would cite them. They are kept with the case as your evidence and shown to the grading model.
- **To grade the AI on an authority, write a key point for it**, such as `+2 Relies on CA 2022/31.` A listed authority is not graded on its own.

## When the right answer depends on facts not given

Do not write a case whose right answer is "it depends". Add the missing fact to the question, or write two cases, one for each version of the fact.

## Review it as you would a junior's memo

Before you save, read the question and your key points side by side and ask: would I accept an answer that earns exactly these points, and nothing more? If yes, save it.
