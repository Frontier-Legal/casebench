# Contributing

Casebench is at an early stage. The most useful contribution today is an issue that describes what you need or what is wrong, with the jurisdiction and the kind of task it concerns.

## Pull requests

- Open an issue first for anything beyond a small fix, so the design is agreed before the code.
- Keep a pull request to one change. Describe what a user will notice and name the test that proves it.
- Commit messages follow [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, with a scope when it helps.
- Sign off every commit with `git commit -s`. This is the [Developer Certificate of Origin](https://developercertificate.org/): you certify that you have the right to submit the change under the project's licence.
- A pull request merges with green CI and one review.

## Decisions

A material choice, such as a new dependency, a public interface or a storage format, gets an architecture decision record under `docs/decisions/` in the same pull request. Copy the latest record as a template.

## Adapters

A jurisdiction adapter is its own package named `casebench-<country>`. The adapter interface and its conformance tests live in this repository. `ADAPTERS.md` will describe the steps once the interface is stable.

## Security

Report a security concern through GitHub's private vulnerability reporting on this repository, under the Security tab, never in a public issue. A security policy with response times will be published before the first release.

## Conduct

A code of conduct will be published before the first release. Until then: be direct, be kind, and assume good faith.
