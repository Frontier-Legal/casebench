---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# One set of checks, locally and in CI, with a pinned supply chain

## Context and problem statement

The repository was public before its first line of code. Firm security reviewers read the workflows and the OpenSSF Scorecard before they read the code. A check that runs only in CI teaches contributors to push and wait; a check that runs only locally is skipped.

## Considered options

- pre-commit locally and the same tools in GitHub Actions, every action pinned by commit SHA
- CI only
- Actions pinned by tag

## Decision outcome

Chosen option: "pre-commit locally and the same tools in CI, pinned by SHA", because the contributor sees the same failure before pushing, and a moved tag cannot change what runs.

- Checks: ruff (lint and format), pyright, pytest, zizmor on the workflows, Commitizen on commit messages, gitleaks on staged changes.
- pytest runs on Linux for every supported Python version, and on macOS and Windows for the oldest and newest. That is 8 jobs, inside the free plan's 20 concurrent jobs and 5 concurrent macOS jobs for public repositories (GitHub Actions limits, checked 2026-10-11).
- Every workflow sets `permissions: {}` or read-only at the top and grants write scopes per job.
- Every action is pinned by full commit SHA, with the version in a comment; Dependabot updates the pins and the uv lockfile weekly.
- CodeQL is the static analysis; the Scorecard action runs weekly and on `main`.
- Each pull request's commits are checked for a `Signed-off-by` trailer (DCO).
- `main` takes changes only through pull requests with green CI, and push protection refuses secrets. Those are repository settings; `.github/rulesets/main.json` holds the ruleset so it is reviewable.
- While the project has one maintainer, the ruleset requires no approving review: GitHub never lets the author of a pull request approve it, so a required review would block every merge. The count goes to 1, with code-owner review, when a second maintainer joins.
- Pull requests opened by `GITHUB_TOKEN`, such as the release pull request, do not trigger other workflows. A maintainer closes and reopens the release pull request to run CI on it.

### Consequences

- Good, because the Scorecard checks for pinned dependencies, token permissions, SAST and dependency updates pass from the first release.
- Bad, because SHA pins are unreadable without the version comment, and Dependabot pull requests add review load.

## Revisit when

A second maintainer joins (raise the review count), the free concurrency limits slow pull requests noticeably, or a check produces more noise than findings.

## More information

- [OpenSSF Scorecard checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md)
- [zizmor](https://docs.zizmor.sh/)
- [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
