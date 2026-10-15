---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# A gate fails a build only on a significant drop, over approved cases, against a saved baseline

Builds on [0028](0028-scores-baselines-and-intervals.md) (paired intervals) and [0035](0035-comparable-and-strict-scores.md) (score sets that say what produced them).

## Context and problem statement

A prompt or model change that lowers legal accuracy ships when nothing in the pipeline measures it. Engineers adopt a check only when it runs where their tests run, and only when it fails for a reason. A gate that fails on noise is switched off within a week. `casebench compare` already pairs two runs of one suite case by case and gives the interval of each metric's difference (0028). It also names every setting the two score sets were produced with differently (0035). It never fails, and it reads draft cases like approved ones.

## Considered options

1. `casebench gate BASELINE RUN` compares two runs of one suite, and exits non-zero when a metric falls significantly. A pytest plugin and a GitHub Action call it.
2. A fixed threshold per metric, such as "citation accuracy at least 90%".
3. Fail on any drop.

## Decision outcome

Chosen option 1, because only a drop larger than the run-to-run noise says the change made the agent worse. Option 2 fails a suite that was always hard and passes one that fell from 99% to 91%. Option 3 fails on noise.

- **What fails.** A metric whose paired interval of the difference lies wholly on the worse side of zero, in its own direction (0028). The gate exits 1 and names the metric. It also names the error types that grew from the baseline to the run, each with both counts:
  - a citation's label, such as fabricated or misgrounded;
  - the kind of a failed criterion;
  - otherwise the score's label.

  A drop inside the interval is reported and does not fail.
- **What cannot be judged.** The gate exits 2, without failing on any metric, when:
  - the two runs ran different suites;
  - a setting that moves a metric differs between the two score sets (0035), such as another judge.

  Comparing them would credit or blame the agent for a change in the measurement.
- **Approved cases only.** By default the gate pairs only cases a lawyer approved, and reports how many draft cases it left out. A suite with no approved case is reported as such, and the gate passes: there is nothing to gate yet.
  - `--include-unreviewed` pairs draft cases too, such as court-derived cases no lawyer has read yet, and says so on its first line.
- **Cost and latency** are reported, before and after, and never fail the gate.
- **The commit.** A run records the commit it ran at in `run.json`, so a baseline and a run name their code. It takes `--commit`, else `GITHUB_SHA`, else `git rev-parse HEAD` in the current folder, else none.
- **The pull request comment.** `casebench gate --markdown FILE` writes a table: each metric before and after, the interval of the difference, and whether the change is significant, with the error types that grew and the cases left out.
- **pytest.** Casebench registers a pytest plugin. A test marked `@pytest.mark.casebench(suite=..., baseline=...)` runs the suite with the project's `casebench.yaml`, as `casebench run` does, then the gate. The test fails when the gate fails, with the gate's report as its message.
- **GitHub.** The repository ships a composite action, `Frontier-Legal/casebench@<ref>`. It installs Casebench with uv, runs the suite, runs the gate against the baseline folder it is given, and posts or updates one comment on the pull request. It needs `pull-requests: write`. Every action it uses is pinned by commit SHA.
- **The baseline** is a run folder the team keeps: committed to the repository, or restored from an artifact. The gate reads it and never writes to it.

### Consequences

- Good, because a failing build names the metric, the size of the drop and the error types behind it.
- Good, because a change of judge or corpus cannot pass or fail a build silently.
- Bad, because a small suite has wide intervals, so only large drops fail it. The report shows the interval, so the team sees why.
- Bad, because the baseline must be run again whenever the measurement changes, and the gate says so by exiting 2.

## Revisit when

- Teams ask the gate to fail on cost or latency.
- Teams want a gate on a metric's level, not only its change.

## More information

- [0028](0028-scores-baselines-and-intervals.md), [0035](0035-comparable-and-strict-scores.md).
- GitHub's documentation on composite actions and on `GITHUB_SHA`.
