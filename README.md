# Casebench

Casebench measures the legal accuracy of an AI system against real court decisions and lawyer-written references, in any jurisdiction.

**Status:** early development. There is nothing to install yet; the first release will be announced here. Casebench follows [SemVer](https://semver.org/), and while the version is 0.x any minor release may break the command line, the file formats or the Python interface. The changelog names every break.

## What it will do

- Build evaluation cases from court decisions a team already holds: the ruling, the statutes applied and the precedents relied on, each fact pointing at a passage in the decision.
- Take lawyer-written cases from a spreadsheet, for question answering, research, drafting, editing and extraction tasks.
- Check every citation in every answer against the corpus: does the authority exist, and does it say what the answer claims?
- Show where in a multi-step system the right authority was lost: retrieved, kept, read, cited, characterised.
- Report per task, per metric and per reference source, with the failing example beside every rate. There is no single accuracy number.

## Jurisdictions

Lawyer-written cases work in any country with no adapter. Court-derived cases and citation checks need the adapter package for that country, published separately as `casebench-<country>`. Türkiye is the first. [ADAPTERS.md](ADAPTERS.md) explains how to add one.

## Principles

- Nothing leaves your machines except calls to the system under test and the judge you configure. There is no telemetry.
- The grader never asks the system it grades.
- Every result reruns on your own corpus with the open-source code. A shared server, hosted or self-hosted, stores and shows results and never computes a score.
- Frontier Legal, which maintains Casebench, publishes no rankings of products, and neither does the project.

## Documentation

- [docs/design/](docs/design/) describes how Casebench works.
- [docs/decisions/](docs/decisions/) records why it is built that way.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The rules for changing the code are in [AGENTS.md](AGENTS.md). Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md). Report security issues as [SECURITY.md](SECURITY.md) describes.

## Licence

Apache-2.0, except the `ee/` directory, which holds the multi-user team server under its own source-available licence. [LICENSE](LICENSE) states the boundary.
