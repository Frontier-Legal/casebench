---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Suites and run logs are JSON Lines with a manifest

## Context and problem statement

A published result is only worth something if a third party can rerun the exact suite and get the same cases in the same order. Lawyers and engineers also need to read, diff and review suites in a pull request, and a crashed run must resume without losing finished work. Scores must be recomputable from a finished run with newer metrics, without calling the system under test again.

## Considered options

- JSON Lines files plus a JSON manifest, in plain folders
- One JSON document per suite and per run
- SQLite files
- Parquet

## Decision outcome

Chosen option: "JSON Lines plus a manifest, in plain folders", because a line per record diffs and reviews well, appending a line is how a run persists each result before the next, and any language can read it.

A suite is a folder:

- `suite.jsonl`: one case per line, in the suite's order.
- `manifest.json`: the suite id, the content hash, the Casebench version that froze it, the number of cases and the mix of task types, reference sources and approval states.

The content hash is SHA-256 over the cases in order, each serialised as canonical JSON: keys sorted, no insignificant whitespace, UTF-8, one case per line. A suite generated from the same inputs with the same suite id produces the same lines in the same order, because any sampling is seeded from the suite id.

A run is a folder `runs/<run_id>/`:

- `run.json`: the run id, the suite id and hash it ran, the target's name and the Casebench version.
- `results.jsonl`: one line per case per repeat, appended as each finishes.
- `scores/<score_set_id>.jsonl`: one line per score. Every scoring pass writes a new score set; existing score sets are never rewritten.

### Consequences

- Good, because a run can be re-scored by reading `results.jsonl` alone; the target is not involved.
- Good, because a reviewer reads a suite change in a pull request as added and removed lines.
- Bad, because large suites and runs are larger on disk than a binary format. Corpora are never copied into either, only ids and evidence excerpts.

## Revisit when

Suites or run logs reach sizes where JSON Lines is slow to read, or a standard eval log format becomes the one users expect.

## More information

- [JSON Lines](https://jsonlines.org/)
- [RFC 8785, JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785), which the canonical form follows for key order and whitespace.
