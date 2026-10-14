---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# Setup spends one search and one document, and ends with a one-case demo

Amends [0025](0025-corpus-connectors.md) (how much a check samples), [0044](0044-onboarding-by-a-coding-agent.md) (how setup ends) and [0039](0039-one-case-by-a-lawyer.md) (who drafts a case).

## Context and problem statement

The first real setup by a coding agent ran on 2026-10-14 against a production legal agent whose document API is metered per search. `casebench check` searched that API for up to 200 results, and would have fetched each one, every time the coding agent ran it. 0044 had made `check` reuse the corpus's probe search, and it did so at the corpus check's sample size of 200 (0025). A setup needs to know only that the store answers and that its fields map. One search for one result, and one document, show that.

Setup also ended with three lines saying passed or failed. None of them shows what Casebench does: a case from the user's own court decisions, the agent's answer, and a grade a lawyer can read.

## Considered options

1. `check` spends one search and one document. A new `casebench demo` drafts one case from one decision, asks the agent, grades the answer in one judge call, and shows a table, after saying what it will spend.
2. Keep `check`'s sample at 200, and have the guide pass `--size 1`.
3. End setup with `casebench run` on a one-case suite.

## Decision outcome

Chosen option 1. A setup step should cost what it says, whoever runs it and however often. Option 2 leaves the cost to whoever remembers the flag. Option 3 resolves every citation in the answer with a corpus search, so its cost depends on the answer.

- **`check` during setup.** Its corpus part searches once, for one result, and fetches that document. The 200-document sample stays with `casebench corpus check`, which samples only when it is run, with `--size` to say how many.
- **`casebench demo`.** It says first what it will spend: 1 search, 1 document, 1 drafting call, 1 agent turn, and 1 grading call, or 2 with a second judge. Then:
  - it searches the corpus with its probe search for one result and fetches it;
  - the first extraction model, or else the judge, drafts a case from it as `case new` does (0039): a question the decision answers, its facts, the outcome, and the statutes and precedents the court relied on, each kept only where its quote is in the text;
  - the case gets one more criterion, that the answer cites the decision itself, written by Casebench from the citation the corpus gave for it;
  - the agent is asked the question, as a run asks it, with its calls recorded;
  - the criteria metric grades every criterion in one call per judge;
  - a table shows the question, what the court decided, the agent's answer, and each criterion with its result and the quote that shows it.
- **The demo's case** is kept as a draft under `.casebench/demo/`, with the agent's answer. A lawyer can approve it into a suite later. It is never a reference until a lawyer approves it.
- **A corpus's name.** `corpus add --name` turns what it is given into the form `casebench.yaml` accepts, such as `frontier-legal` for "Frontier Legal", and says so.

### Consequences

- Good, because setup's cost is known in advance and is the same each time: a check is one search and one document, and a demo is five or six calls.
- Good, because setup ends by showing what Casebench measures, on the user's own decisions and the user's own agent.
- Bad, because the demo's case is drafted by a model and graded by a model, with no lawyer in between. The table says so, and the case stays a draft.
- Bad, because the demo checks only whether the answer cites the decision the case came from, not every authority it cites. A run checks those.

## Revisit when

- A store whose search returns no result for its probe makes the check or the demo fail on a store that works.
- Lawyers ask for more than one case in the demo.

## More information

- The first real setup's report, 2026-10-14: the coding agent's `check` runs against the metered document API, stopped by the user.
