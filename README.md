# Casebench

Casebench measures the legal accuracy of an AI system against real court decisions and lawyer-written references, in any jurisdiction.

**Status:** early development. Casebench is on [PyPI](https://pypi.org/project/casebench/). It follows [SemVer](https://semver.org/), and while the version is 0.x any minor release may break the command line, the file formats or the Python interface. The changelog names every break.

## What it will do

- Build evaluation cases from court decisions a team already holds: the ruling, the statutes applied and the precedents relied on, each fact pointing at a passage in the decision.
- Take lawyer-written cases from a spreadsheet, for question answering, research, drafting, editing and extraction tasks.
- Check every citation in every answer against the corpus: does the authority exist, and does it say what the answer claims?
- Show where in a multi-step system the right authority was lost: retrieved, kept, read, cited, characterised.
- Report per task, per metric and per reference source, with the failing example beside every rate. There is no single accuracy number.
- Give lawyers a review queue in the browser, on a laptop or a phone: the evidence beside each answer, the judge's verdict filled in, one key per verdict.

## Set it up

Paste this into the coding agent you use in your project:

> Set up Casebench for this project. Run `uvx casebench guide` and follow it.

The guide has the coding agent read your project and write two things: `casebench.yaml` and an adapter in `.casebench/` that starts your agent the way your production does. Nothing else in your project changes, and no key's value is read or written. It ends when `casebench check` passes, and it asks you one question: which judge model to pay for. Without a coding agent, `casebench init` asks the same things in the terminal.

## Review with lawyers

`casebench ui` opens the review queue on this machine. Lawyers confirm or overrule the judge on each criterion of an answer, read every citation's source passage, and approve, edit or reject the facts of cases drawn from court decisions. Their verdicts replace the judge's in the report and in the gate. `casebench ui --role reviewer` shows only legal text, citations and passages.

## Jurisdictions

Casebench works in any country with no country-specific code. Models read the decisions and the answers, and your corpus resolves every citation, whatever its format. A data provider that serves several countries needs one connector. [PLUGINS.md](PLUGINS.md) explains how to add a data provider or a model API.

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
