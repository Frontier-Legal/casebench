---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# Setup spends one search and one document, and greets the agent once

Amends [0025](0025-corpus-connectors.md) (how much a check samples) and [0044](0044-onboarding-by-a-coding-agent.md) (what setup asks the agent).

## Context and problem statement

The first real setup by a coding agent ran on 2026-10-14 against a production legal agent whose document API is metered per search. `casebench check` searched that API for up to 200 results, and would have fetched each one, every time the coding agent ran it. 0044 had made `check` reuse the corpus's probe search, and it did so at the corpus check's sample size of 200 (0025). A setup needs to know only that the store answers and that its fields map. One search for one result, and one document, show that.

The same `check` asked the agent the corpus's probe topic, a real legal question. That agent takes minutes per answer and runs its own searches and model calls, so a setup check spent as much as a case. Setup needs to know only that the agent starts and answers.

## Considered options

1. `check` spends one search and one document on the corpus, and sends the agent one greeting, "Hi. How are you?". Setup ends when `check` passes.
2. As 1, and end setup with a demo: draft one case from one decision, ask the agent, grade the answer, show a table.
3. Keep `check`'s sample at 200 and its legal question, and have the guide pass smaller sizes.

## Decision outcome

Chosen option 1. A setup step should cost what it says, whoever runs it and however often, and it should take as long as starting the agent, not as long as researching a case.

Option 2 was built and run on 2026-10-14 and removed the same day. It asked the agent a second full legal question after `check`, and setup took 15 minutes. Option 3 leaves the cost to whoever remembers the flags.

- **The corpus part of `check`** searches once, for one result, and fetches that document. The 200-document sample stays with `casebench corpus check`, which samples only when it is run, with `--size` for how many.
- **The agent part of `check`** sends "Hi. How are you?". An answer without an error passes. A greeting asks for no research, so even a slow agent answers it quickly and spends little. `casebench target check --question "…"` asks something else, for anyone who wants to.
- **The guide** lists what each command that calls out spends, and tells the coding agent not to run one twice to look around.
- **A corpus's name.** `corpus add --name` refuses a name `casebench.yaml` would reject, such as "Frontier Legal", before anything is searched, and says what a valid one looks like, such as `frontier-legal`. It does not rewrite a name: what to call the store is the user's choice.

### Consequences

- Good, because setup's cost is known in advance and stays the same each time: 1 search, 1 document, 1 short judge call and 1 greeting.
- Good, because setup takes as long as starting the agent once.
- Bad, because a passing `check` does not show the agent answering a legal question well. That is what a run is for, with a case a lawyer wrote or approved.

## Revisit when

- A store whose search returns no result for its probe makes the check fail on a store that works.
- An agent that will not answer a greeting, such as one that only takes structured legal questions, makes the check fail on an agent that works.

## More information

- The first real setup's report, 2026-10-14: the coding agent's `check` runs against the metered document API, stopped by the user; the later run with the demo took 15 minutes.
