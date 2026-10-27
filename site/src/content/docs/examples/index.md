---
title: Examples
description: Complete setups you can copy, each with the agent, casebench.yaml, the commands and what the report shows.
sidebar:
  label: Overview
  order: 0
---

Each example is a complete setup: the agent, the `casebench.yaml`, the commands in order, and what to read in the report. Copy the one closest to your stack.

| Example | Shows |
| --- | --- |
| [An agent in TypeScript](/examples/walkthroughs/typescript-agent/) | An HTTP target with a `start` command, a Node agent's model calls recorded with no code change, and the host it calls allowed |
| [A retrieval agent with the authority funnel](/examples/walkthroughs/retrieval-funnel/) | A Python agent whose search and model calls are recorded where they go, an in-process rerank, and reading where the right decision was lost |
| [A suite across two jurisdictions](/examples/walkthroughs/mixed-jurisdictions/) | Two corpora, a suite mixed in chosen shares, and per-jurisdiction rows |
| [A nightly run in CI](/examples/walkthroughs/scheduled-ci-run/) | Running a suite every night, gating it against a baseline, and pushing it to a team server, plus the gate on pull requests |

Every example uses decisions and agents of its own. The figures in their reports are illustrative; the layout is what Casebench 0.5.1 prints.

For a first run, start with the tutorial [Your first evaluation](/developers/tutorials/first-evaluation/), or see Casebench work with no key in [the demo](/developers/tutorials/demo/).
