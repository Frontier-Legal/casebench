---
title: Confidentiality
description: What Casebench sends where, in plain terms, for a lawyer answering a client's or a security officer's question.
sidebar:
  order: 4
---

Casebench runs on your firm's own machines. It sends nothing to its makers and has no usage reporting.

## Who sees what

| Who | Sees | Why |
| --- | --- | --- |
| The AI system under test | The test questions and facts | It is what is being tested |
| The grading model your team chose, on your team's account | The AI's answers and the documents needed to check their citations | To grade them |
| The models that read decisions, if your team builds tests from decisions | The decisions | To find the answer key |
| Your source of decisions | Searches for citations | To find what exists |

No one else receives anything. The grading model runs under your firm's own agreement with its provider, so the same terms apply as to any other use of that provider by your firm.

## Client material

Test cases are questions and expected answers. If a case contains facts from a client matter, it is confidential in the same way as any working document. Prefer anonymised facts: the test works as well with "the employer" as with the client's name.

## Where results are kept

The answers, scores and your verdicts are computed and kept on your firm's machines. When your team uses a team server, the engineer sends it the test cases with their evidence excerpts, the AI's answers, the scores, and your verdicts and comparisons. The server never receives the full text of decisions, the AI system's code, the grading model's replies, or any key, and it never computes a score: it stores and shows what was computed on your firm's machines.

Every verdict, change to the answer key and sign-in on the team server is kept in an audit log that nobody can change.

## Related

- For engineers and security officers: [Privacy and what leaves your machine](/developers/concepts/privacy/).
