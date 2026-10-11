---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# A shared server never computes a score

## Context and problem statement

Lawyers review runs in a shared place: a self-hosted team server or a hosted cloud. If that shared place computed scores, a result would depend on code and data a user cannot rerun, and the maintainers would be in a position to rank products, which a neutral yardstick must never do.

## Considered options

- The shared place stores and shows what the user pushes; every score is computed on the user's machines
- The shared place runs suites and computes scores as a service
- No shared place; reviews only through exported files

## Decision outcome

Chosen option: "The shared place stores and shows what the user pushes", because every result then reruns on the user's own corpus with the open-source code, and the maintainers never see a corpus, an agent or an API key.

`casebench push` sends cases, outputs, scores, evidence excerpts and reviews. Traces go only with `--traces`, as ids and numbers, never message content. Human decisions made in the shared place come back through `casebench pull` and outrank a judge's verdict on the next report.

### Consequences

- Good, because a published result is reproducible by anyone with the suite and the corpus snapshot.
- Good, because the maintainers publish no rankings and hold nothing they could rank with.
- Bad, because scheduled runs and comparisons in the shared place must call out to a runner the user controls.

## Revisit when

Users ask for hosted runs strongly enough to accept that their corpus and agent credentials leave their machines, and a design exists that keeps every score reproducible off the server.

## More information

- [../design/workbench.md](../design/workbench.md) describes local, team and cloud modes.
