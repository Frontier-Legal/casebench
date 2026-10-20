---
status: accepted
date: 2026-10-20
decision-makers: Casebench maintainers
---

# Run history: nightly runs from a team's CI land in the cloud's tables, which chart every metric over time

Adds to [0050](0050-the-review-queue.md) (run folders are the truth on the engineer's machine), [0059](0059-push-invite-pull.md) (push and pull) and [0066](0066-one-shared-cloud.md) (one shared cloud). Follows [0005](0005-cloud-never-computes-a-score.md): the cloud never scores.

## Context and problem statement

The operator decided on 2026-10-20 that Casebench is also where a team watches its agent's legal accuracy over time: suites run every night, as CI runs tests, and people see each metric change across runs in charts and tables. Monitoring the agent's live production traffic is a long-term goal, not part of this; evaluation history comes first. Run folders are the right record for one run on an engineer's machine ([0050](0050-the-review-queue.md)), but a chart of ninety nightly runs across many suites and organisations cannot be drawn by reading ninety folders on every page view.

## Considered options

1. Locally nothing changes. In the cloud a push is kept twice: the run's files, unchanged, as an archive in object storage, and their contents loaded into tables that charts and tables query. Nightly runs are scheduled in the team's own CI.
2. Run folders stay the only record in the cloud too, with an index rebuilt from them.
3. The cloud runs each suite on a schedule itself.

## Decision outcome

Chosen option 1, because history is the cloud's main view and the tables are what it reads, while the archive keeps every pushed file as the runner wrote it. Option 2 treats the history a customer pays for as a cache. Option 3 has the cloud score runs, which [0005](0005-cloud-never-computes-a-score.md) rules out, and has it call agents inside each firm's network.

- **On the engineer's machine and in CI, files stay the truth.** `run`, `report`, `gate` and re-scoring read run folders and need no server ([0050](0050-the-review-queue.md)).
- **In the cloud, the tables are the record.** A push stores the run's files as they are, then loads them, in the same transaction, into tables: the run (suite, its hash, commit, time, target), each case's result, each score by metric, reference source and practice area with its interval, the error rates, what it spent and how long it took. A run's files can be loaded again from the archive.
- **Charts read the tables.** For each suite, each metric is shown run by run with its interval, by practice area and reference source, and any two runs open side by side ([0054](0054-compare-blind-and-a-report-for-partners.md)). There is still no single accuracy number.
- **Nightly runs come from the team's CI.** A scheduled CI job runs `casebench run`, then `casebench gate` against the baseline ([0048](0048-a-gate-in-ci.md)), then `casebench push`. The runner computes every score and the gate's result, so the cloud only shows them and emails the team when a pushed run's gate failed.
- **Steps go up as numbers.** With `--traces`, each result's steps arrive as ids and numbers ([0059](0059-push-invite-pull.md)) and are kept with the run, so the harness view and per-step charts work in the cloud.
- **Postgres holds it.** At 100 organisations, 5 suites each, 500 cases a suite and one run a night, results grow by about 90 million rows a year, which Postgres serves with the results table partitioned by month. A columnar store is decided when live production traffic is taken on, since its spans are far more numerous than evaluation results.

### Consequences

- Good, because a team sees each night's run among the others, and a drop is announced the morning after.
- Good, because every score in the cloud is the runner's, and the archive keeps the files it came from.
- Bad, because the cloud keeps a run twice, as files and as rows.
- Bad, because the schedule lives in each team's CI, not in a screen in the cloud; the cloud gives the workflow file to copy.

## Revisit when

- The agent's live production traffic is taken on: then where spans are stored is decided again.
- Loading or charting a suite's history becomes slow at the volumes measured then.
