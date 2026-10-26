---
title: Gate a pull request on a run
description: Fail a build only when a metric falls significantly below a saved baseline, over lawyer-approved cases, from the command line, from pytest or with the GitHub Action.
sidebar:
  order: 4
---

`casebench gate` compares a run with a saved baseline run of the same suite. It fails only when a metric falls by more than the run-to-run noise, so a build does not fail on chance.

```sh
casebench gate baselines/employment .casebench/runs/pr-118
```

## What it prints

```text frame="terminal"
qa · citation_integrity: 67% -> 50% over 6 cases, difference -50% to +0%, not significant
  misgrounded citations: 1 -> 2
qa · criteria: 96% -> 58% over 6 cases, difference -71% to -8%, worse, significant
  failed rule criteria: 1 -> 4
1 draft cases were left out; a lawyer has not approved them
latency: 1 -> 1 ms per case (reported, never gated)
gate: failed
```

For each task and metric: the score before and after, the cases paired, the 95% interval of the difference, and its verdict. Under a metric, each error type that grew is listed with both counts. An error type is a citation's label, such as `misgrounded` or `fabricated`, the kind of a failed criterion, or else the score's own label.

Mean latency and mean agent tokens per case are reported and never gated.

## Exit codes

| Code | When |
| --- | --- |
| `0` | No metric fell significantly. A drop inside the interval is reported and passes. |
| `1` | A metric fell significantly: its interval lies wholly on the worse side of zero, in the metric's own direction. |
| `2` | The gate cannot judge: the two runs ran different suites, a setting that moves a metric differs, such as another judge, or a run has no scores yet. |

Exit 2 prints why and writes no Markdown:

```text frame="terminal"
gate: cannot judge: the two runs ran different suites; gate runs of one suite
```

When the judge, a judge prompt, a corpus or the extraction models changed, run the suite again with the new settings and keep that run as the new baseline. Comparing across the change would credit or blame your agent for a change in the measurement.

## Which cases it gates

The gate compares the scores the report shows: a lawyer's verdict on a criterion replaces the judge's. A lawyer who overrules the judge on the baseline or the run changes the gate's result without scoring either again.

By default it pairs only cases a lawyer approved, and says how many draft cases it left out. A suite with no approved case passes, with `0 approved cases: nothing to gate yet`.

`--include-unreviewed` pairs draft cases too, such as court-derived cases no lawyer has read yet, and says so on its first line:

```text frame="terminal"
gating approved and unreviewed cases (--include-unreviewed)
```

## The pull request comment

`--markdown FILE` writes the same result as a Markdown table:

```sh
casebench gate baselines/employment .casebench/runs/pr-118 --markdown gate.md
```

```md title="gate.md"
<!-- casebench-gate -->
### Casebench gate

| Task · metric | Before | After | Cases | Difference | Change |
|---|---|---|---|---|---|
| qa · citation_integrity | 67% | 50% | 6 | -50% to +0% | not significant |
| qa · criteria | 96% | 58% | 6 | -71% to -8% | worse, significant |

Error types that grew:

- citation_integrity: misgrounded citations, 1 -> 2
- criteria: failed rule criteria, 1 -> 4

1 draft cases were left out; a lawyer has not approved them.

Reported, never gated: latency: 1 -> 1 ms per case.

**Gate failed.**
```

The first line is a marker the GitHub Action uses to find and update its own comment.

## Keep a baseline

A baseline is a run folder you keep: committed to the repository, or restored from a CI artifact. The gate reads it and never writes to it. It needs the folder's `run.json`, `results.jsonl`, `scores/` and, when lawyers reviewed it, `reviews.jsonl`.

`.casebench/` is ignored by git, so copy a run you want to keep out of it:

```sh
cp -R .casebench/runs/main-2026-10-20 baselines/employment
git add baselines/employment
```

Each run records the commit it ran at in `run.json`, so the baseline names its code.

## In pytest

Installing Casebench registers a pytest plugin. Mark a test with the suite and the baseline:

```python title="tests/test_legal_accuracy.py"
import pytest


@pytest.mark.casebench(suite="suites/employment", baseline="baselines/employment")
def test_legal_accuracy():
    pass
```

Before the test's body runs, the plugin runs the suite as `casebench run` would, with the project's `casebench.yaml`, then the gate. The test fails when either fails, with the gate's report as its message:

```text
Casebench gate failed (exit 1):
qa · citation_integrity: 67% -> 50% over 6 cases, difference -50% to +0%, not significant
```

The message goes on with the rest of the gate's report.

The marker takes `config` (default `casebench.yaml`), `runs_dir` (default `.casebench/runs`) and `include_unreviewed` (default `False`). Each test run gets a new run id: `pytest-`, the time and a random suffix.

## With the GitHub Action

The Casebench repository is a composite action. It installs uv, runs the suite as `gate-$GITHUB_SHA`, gates it against the baseline, posts or updates one comment on the pull request, and fails the job when the gate fails.

```yaml title=".github/workflows/casebench-gate.yml"
name: casebench gate

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  gate:
    runs-on: ubuntu-latest
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      COURTS_API_KEY: ${{ secrets.COURTS_API_KEY }}
    steps:
      - uses: actions/checkout@v5
        with:
          persist-credentials: false
      - uses: Frontier-Legal/casebench@v0.5.1
        with:
          suite: suites/employment
          baseline: baselines/employment
          casebench: uv run --with casebench==0.5.1 casebench
```

Pin each action to a full commit SHA in your own repository; the tags above keep the example readable.

| Input | Default | Meaning |
| --- | --- | --- |
| `suite` | required | The frozen suite's folder |
| `baseline` | required | The baseline run's folder, committed or restored from an artifact |
| `config` | `casebench.yaml` | The config to run with |
| `include-unreviewed` | `"false"` | `"true"` gates the cases no lawyer has approved too |
| `casebench` | `uvx casebench` | The command that runs Casebench |

A Python agent needs its own dependencies, so set `casebench` to run inside the project's environment, as above. The action has one output, `code`: the gate's exit code.

The action writes its run to `.casebench/runs/gate-<sha>/`. It comments only on `pull_request` events, and needs `pull-requests: write` for that. A gate that could not judge writes no comment; the job log says why, and the job fails with exit code 2.

## Related

- [Compare two runs](/developers/guides/runs/compare-runs/).
- [A nightly run in CI](/examples/walkthroughs/scheduled-ci-run/).
- [Scores, intervals and baselines](/developers/concepts/scores/).
