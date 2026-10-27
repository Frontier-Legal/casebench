---
title: What a score means
description: Why every figure comes with a range, what the two baselines are for, and why Casebench gives no single accuracy number.
sidebar:
  order: 3
---

A Casebench score answers one narrow question: on these cases, of this kind, graded this way, how often was the AI right? Three things come with it, and each one stops a common misreading.

## The range

Every score has a 95% interval, such as "71%, between 62% and 78%". It says how much the figure could move on another set of cases of the same size. A small test gives a wide range, and the range is the honest answer: with 24 cases, Casebench cannot tell 79% from 70%.

When two versions of an AI are compared, by scores or by lawyers' blind preferences, Casebench marks a difference "not significant" when it could be chance. Treat such versions as equal. See [Compare two versions](/lawyers/guides/compare-versions/).

## Error rates

The Reports page leads with error rates rather than scores: the share of answers that cited an authority that does not exist, cited one for something it does not say, stated the wrong outcome, or relied on a statute the court did not apply. Each comes with its range, and each opens the answers behind it. Lawyers' verdicts count in place of the grading model's.

## The baselines

For questions about how a court ruled, two simple guesses are scored beside the AI:

- **Majority**: always answering the most common outcome. If most appeals in the test were dismissed, this guess scores high without any legal reasoning.
- **Text-only**: a simple program that counts words in the facts and predicts the outcome. If it scores high, the facts give the ruling away, and the test is too easy.

The AI is doing legal work only to the extent it beats both, by more than the range.

## No single number

There is no overall accuracy figure. Each kind of question, each way of grading, each source of answer key and each jurisdiction gets its own row. In the report's tables, approved and unreviewed answer keys are never averaged together. The error rates on the Reports page count every answer; the report exported for partners counts approved cases only.

That is deliberate. An average of outcome prediction and open questions, or of Turkish and Norwegian law, describes nothing anyone uses. It also lets a vendor hide a weak area behind a strong one.

## The strict reading

For questions graded by a lawyer's checks, the report also gives "all passed": how many answers met every check. An answer that makes four of five required points and misses the decisive one is wrong in practice, and this figure counts it as wrong.

## Training cutoff

AI models learn from published text, which may include the decisions in a test. Your engineer can build tests only from decisions published after the model's training cutoff, and the suite records that date. Ask for it when a score looks too good.
