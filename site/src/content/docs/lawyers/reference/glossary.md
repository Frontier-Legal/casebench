---
title: Glossary
description: Every term a lawyer meets in the Casebench workbench, in plain words.
sidebar:
  order: 1
---

**AI under test, agent, target.** The AI system Casebench is testing: your firm's assistant, or a vendor's product.

**All passed.** The share of answers that earned every positive key point and made none of the errors a negative key point describes.

**Answer key, golden data.** Every case's question, reference answer and key points. Every score rests on it. You keep it under **Golden data**.

**Approved.** A case a lawyer has checked and accepted. Its results count as lawyer-approved.

**Audit log.** The record of every verdict, change to the answer key and team event: who, when, before, after and why. Nothing in it can be changed or removed.

**Baseline.** A simple guess scored beside the AI, to show what a score means. "Majority" always guesses the most common outcome; "text-only" predicts from the words of the facts alone.

**Case.** One test: a question, the answer you expect and the key points it is graded on.

**Citation check.** Looking up a citation in your sources and deciding whether it exists and supports what the answer claims.

**Court draft.** A case Casebench drafted from a court decision, waiting for a lawyer to approve, edit or reject each fact.

**Corpus, sources.** The decisions and statutes your firm connects. Casebench looks up every citation there.

**Error rate.** The share of answers with one kind of error, such as a fabricated citation, with its range.

**Fabricated, not found.** A citation to an authority that does not exist in a source covering that jurisdiction. Underlined in red.

**Fingerprint, hash.** A long code that identifies the exact cases in a suite. Any change to any case changes it.

**Interval, range.** How much a figure could move on another set of cases of the same size. "14%, between 0% and 57%."

**Judge, grading model.** The AI model your team chose to read answers, match citations and suggest a verdict on each point. It never decides what exists and never overrules you.

**Jurisdiction.** Written as a country code: `GB`, `TR`, `NO`; a state or region as `US-CA`; European Union law as `EU`.

**Key point.** One pass-or-fail point a correct answer must make, with a weight: `+3` earned when it is made, `-3` lost when an error is made.

**Misgrounded, misused.** A citation to a real authority that does not say what the answer claims. Underlined in orange.

**Not significant.** A difference between two versions that could be chance. Treat the two as equal.

**Outcome.** How the court ruled, as one word: `upheld`, `reversed`, `partly_reversed`, `remanded`, `granted`, `rejected`, `partly_granted` or `dismissed`.

**Overrule.** Giving a verdict other than the judge's suggestion, with a note saying why. Your verdict replaces the judge's everywhere.

**Practice area.** The area of law a case belongs to, as your team names it, such as `employment`. Reports give each figure by practice area.

**Reference answer.** The answer you would give to a case's question. The judge reads it as your evidence.

**Review queue.** The list of answers and court drafts waiting for a lawyer.

**Run.** One pass of a suite through the AI under test, named by your team, such as `after-prompt-fix`.

**Suite.** A named set of cases, run together.

**Team server.** The workbench on a server your firm runs, with sign-in, roles and an audit log.

**Training cutoff.** The date after which an AI model has read nothing. Tests built from later decisions cannot be answered from memory.

**Unchecked.** A citation Casebench could not look up, because no connected source covers its jurisdiction. It does not count against the AI.

**Unreviewed, draft.** A case no lawyer has approved yet. In the report's tables its results have their own row. The Reports page's error rates count it with the rest; the report for partners leaves it out.

**Verified, supported.** A citation to a real authority that supports what the answer claims. Underlined in green.

**Workbench.** The web app where lawyers review answers, keep the answer key and read reports.
