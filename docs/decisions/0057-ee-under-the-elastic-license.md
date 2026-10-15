---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# `ee/` is under the Elastic License 2.0, and the rest of the repository under Apache-2.0

Amends [0004](0004-open-core-and-ee-boundary.md) (open core and the `ee/` boundary).

## Context and problem statement

[0004](0004-open-core-and-ee-boundary.md) put `ee/` under a source-available licence whose text was still to be written and reviewed by counsel, and kept `ee/` empty until then. It also tied what goes into `ee/` to what produces a score. The team server ([workbench.md](../design/workbench.md)) is ready to be built, and a licence written for this project alone would need the review 0004 waited for.

## Considered options

1. The Elastic License 2.0, unchanged, for `ee/`.
2. The Functional Source License, which turns each version into Apache-2.0 two years after its release.
3. A licence written for Casebench.

## Decision outcome

Chosen option 1, because it is a published licence many projects use unchanged: it lets anyone use, copy, change and redistribute the code, and forbids offering it to others as a hosted or managed service. Option 2 releases each version for hosting by others after two years. Option 3 needs the review that kept `ee/` empty.

- `ee/LICENSE` holds the Elastic License 2.0, word for word. Every source file under `ee/` starts with `SPDX-License-Identifier: Elastic-2.0`, and a test checks it.
- Everything outside `ee/` is under Apache-2.0, as before. `LICENSE` states the boundary.
- `ee/` is built and packaged on its own, as `casebench-ee`, and plugs into the core through the core's entry points. The core never imports from `ee/`, so the Apache-2.0 package works without it. A test checks this.
- Which features go into `ee/` is the maintainers' choice, feature by feature.
- `ee/` takes no outside contributions for now. The core takes them with a DCO sign-off, as before.
- This replaces 0004's terms for `ee/`: its licence to be written and reviewed by counsel, a contributor licence agreement for `ee/`, and the rule tying the boundary to what produces a score.

### Consequences

- Good, because `ee/` can hold code now, under terms readers already know.
- Good, because the core installs and runs without `ee/`.
- Bad, because the Elastic License 2.0 is not an open-source licence, so `ee/` is source-available, not open source.

## Revisit when

- Outside contributors want to work on `ee/`, which needs a contributor agreement.

## More information

- [Elastic License 2.0](https://www.elastic.co/licensing/elastic-license); SPDX identifier `Elastic-2.0`.
