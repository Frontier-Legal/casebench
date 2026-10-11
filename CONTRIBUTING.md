# Contributing

Casebench is at an early stage. The most useful contribution today is an issue that describes what you need or what is wrong, with the jurisdiction and the kind of task it concerns.

## Set up

```
uv sync
uv run pre-commit install
```

`pre-commit` then runs ruff, pyright, zizmor, gitleaks and the commit-message check on every commit, and pytest before every push. CI runs the same checks, with pytest on Linux, macOS and Windows.

## Pull requests

- Open an issue first for anything beyond a small fix, so the design is agreed before the code.
- Keep a pull request to one change. Describe what a user will notice and name the test that proves it. A behaviour described as a scenario gets one test named after that scenario.
- A pull request merges with green CI and one review.

## Commits

Commit messages follow [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/). The version number and the changelog are generated from them, so the type matters:

```
feat(corpus): read decisions from an MCP server
fix: keep the case order stable when a suite is regenerated
docs: explain the authority funnel labels
feat(report)!: write scores per reference source

BREAKING CHANGE: report.json groups rows by reference source.
```

`feat` bumps the minor version, `fix` the patch version, and a `!` or a `BREAKING CHANGE:` footer marks a break. While the version is 0.x a break bumps the minor version.

Sign off every commit with `git commit -s`. This is the [Developer Certificate of Origin](https://developercertificate.org/): you certify that you have the right to submit the change under the project's licence. Contributions to `ee/` also need a contributor licence agreement.

## Decisions

A material choice, such as a new dependency, a public interface or a storage format, gets an architecture decision record under [docs/decisions/](docs/decisions/) in the same pull request. Copy [template.md](docs/decisions/template.md).

## Plugins

A data provider, a model API's parser or a model provider is a plugin: built into the core or published as a `casebench-<name>` package. [PLUGINS.md](PLUGINS.md) describes the steps.

## Security

Report a security concern as [SECURITY.md](SECURITY.md) describes, never in a public issue.

## Conduct

Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).
