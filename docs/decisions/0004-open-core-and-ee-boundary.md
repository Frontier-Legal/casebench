---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Open core: Apache-2.0 everywhere except `ee/`

## Context and problem statement

Casebench only works as a yardstick if the vendors being measured can read, run and fork everything that produces a score. Adapter contributors in other countries will not build for code someone else can close. A hosted team server for lawyers costs money to run, and a licence that lets anyone resell it as a service removes the reason to fund it. Firm security reviews read the licence before anyone runs a command, so the boundary must be clear from the first public commit.

## Considered options

- Apache-2.0 for everything that produces or changes a score; a source-available licence for the multi-user team server under `ee/`
- Apache-2.0 for everything
- The whole project under FSL or ELv2
- AGPL-3.0 for everything

## Decision outcome

Chosen option: "Apache-2.0 core, source-available `ee/`", because everything a score depends on stays open and forkable, while the multi-user layer (roles, single sign-on, audit, invites, the server side of push and pull) can fund the project.

`LICENSE` names `ee/` as the only path under the other licence; every file under `ee/` carries a header saying so. The `ee/` licence lets any organisation run the team server for itself and forbids offering it to third parties. Contributions to the core need only a DCO sign-off; contributions to `ee/` also need a CLA, so that directory can be relicensed for a hosted service.

### Consequences

- Good, because a vendor can audit, fork and self-host every metric, adapter and report.
- Good, because the single-user workbench, the CLI and the SDK are fully open.
- Bad, because two licences need a clear boundary, a header check in CI and a CLA flow for one directory.
- Bad, because the `ee/` licence text must be reviewed by counsel before any code is published under it. Until then `ee/` holds no code.

## Revisit when

A second organisation co-maintains the project, or the hosted service is dropped, or the `ee/` licence text fails counsel review.

## More information

- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [Developer Certificate of Origin](https://developercertificate.org/)
- Langfuse uses the same layout: an `ee/` directory with its own licence inside an otherwise permissive repository.
