---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# No telemetry

## Context and problem statement

Casebench runs next to privileged client data: decisions, matter facts, a firm's agent and its API keys. Firm security reviews check what a tool sends home before approving it.

## Considered options

- No telemetry at all
- Opt-in anonymous usage telemetry
- Opt-out usage telemetry

## Decision outcome

Chosen option: "No telemetry at all", because nothing Casebench could learn from usage counts is worth a security review's objection, and an opt-in switch is still code a reviewer has to audit.

Nothing leaves the user's machines except calls to the system under test and the judge or extraction models the user configured, plus what the user explicitly pushes to a shared server. The runner refuses hosts outside the configured allowlist.

### Consequences

- Good, because the answer to "what does it send?" is one sentence.
- Bad, because adoption can only be measured from what users choose to tell the maintainers: issues, discussions and an opt-in run registry later.

## Revisit when

Never by default. Only if users themselves ask for an opt-in registry of runs, and then as a separate, explicit command.
