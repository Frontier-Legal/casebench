# Casebench

Casebench measures the legal accuracy of an AI system against real court decisions and lawyer-written references, in any jurisdiction.

**Status:** early development. There is nothing to install yet; the first release will be announced here.

## What it will do

- Build evaluation cases from court decisions a team already holds: the ruling, the statutes applied and the precedents relied on, each fact pointing at a passage in the decision.
- Take lawyer-written cases from a spreadsheet, for question answering, research, drafting, editing and extraction tasks.
- Check every citation in every answer against the corpus: does the authority exist, and does it say what the answer claims?
- Show where in a multi-step system the right authority was lost: retrieved, kept, read, cited, characterised.
- Report per task, per metric and per reference source, with the failing example beside every rate. There is no single accuracy number.

## Jurisdictions

Lawyer-written cases work in any country with no adapter. Court-derived cases and citation checks need the adapter package for that country, published separately as `casebench-<country>`. Türkiye is the first.

## Principles

- Nothing leaves your machines except calls to the system under test and the judge you configure. There is no telemetry.
- The grader never asks the system it grades.
- Casebench publishes no rankings of products. Every result reruns on your own corpus.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The rules for changing the code are in [AGENTS.md](AGENTS.md).

## Licence

Apache-2.0. See [LICENSE](LICENSE).
