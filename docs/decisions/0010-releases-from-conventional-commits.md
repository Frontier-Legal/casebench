---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Versions and changelog come from Conventional Commits

## Context and problem statement

A version number should say what broke, and a changelog written by hand drifts from what shipped. Firm security reviewers also ask where a wheel came from. A release should be one deliberate action, not a sequence of manual steps.

## Considered options

- release-please reading Conventional Commits, opening a release pull request; PyPI Trusted Publishing with attestations
- python-semantic-release, releasing on every push to `main`
- Commitizen's `cz bump` run by a maintainer
- Manual versions and changelog

## Decision outcome

Chosen option: "release-please with Trusted Publishing", because the release pull request shows the next version and the changelog before anything ships, merging it is the single release action, and it supports several packages in one repository.

- Commits follow [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/). Commitizen's `cz check` validates messages in the `commit-msg` hook and, over the pull request's range, in CI.
- Versions follow [SemVer](https://semver.org/). While the version is 0.x, a breaking change bumps the minor version (`bump-minor-pre-major`), and the changelog lists it under its own heading.
- Merging the release pull request tags the release and writes that version's section of `CHANGELOG.md`. Build and publish run as separate jobs; only the publish job gets `id-token: write`. `pypa/gh-action-pypi-publish` produces PEP 740 attestations by default, which `uv publish` alone does not.
- No commit message names an internal tracker.

### Consequences

- Good, because the version and the changelog cannot disagree with the history.
- Good, because a reviewer can verify a wheel's provenance on PyPI.
- Bad, because a badly typed commit type produces the wrong bump; the commit check catches the format, a reviewer catches the type.

## Revisit when

Releases need a cadence other than "when the release pull request is merged", or release-please stops supporting the uv workspace layout.

## More information

- [release-please](https://github.com/googleapis/release-please)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [PyPI attestations](https://docs.pypi.org/attestations/producing-attestations/)
- [Commitizen check](https://commitizen-tools.github.io/commitizen/commands/check/)
