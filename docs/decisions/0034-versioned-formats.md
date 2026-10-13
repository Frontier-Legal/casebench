---
status: proposed
date: 2026-10-13
decision-makers: Casebench maintainers
---

# Casebench formats are versioned JSON Schemas generated from the models

## Context and problem statement

Casebench should give legal AI builders, data providers and buyers formats they can all rely on. A provider can serve documents in them, a firm can write test cases once and run them anywhere, and a buyer can compare two reports. Today these shapes exist only as pydantic models inside the package. None of them is published, and no file says which version of its shape it is. While the package is 0.x, a minor release may break (AGENTS.md), so nobody outside can build on a shape that may change in any release. The project is public and partly open source: whatever is published must sit on the Apache-2.0 side and must not depend on `ee/`.

## Considered options

1. JSON Schemas generated from the pydantic models, each format versioned apart from the package, and a test that keeps them in step
2. A written specification as the source of truth, with schemas and code following it
3. Adopt existing formats for everything and define none
4. Publish nothing until a second organisation asks

## Decision outcome

Chosen option: "generated schemas, versioned per format", because it publishes the shapes others need without a second source of truth that drifts from the code.

- **Formats.** Five, each named `casebench.<name>`:
  - `document`, a corpus document (`DecisionRecord`, [0025](0025-corpus-connectors.md));
  - `profile`, a data provider profile ([0033](0033-data-provider-profiles.md));
  - `case`, one evaluation case, a line of `suite.jsonl`;
  - `suite`, a suite's `manifest.json` ([0015](0015-suite-and-run-log-formats.md));
  - `report`, a run's `report.json`.

  Run logs and `casebench.yaml` also get schemas, for tools and editors, but they follow the package version, not this promise: re-scoring a run is Casebench's own job, and the config describes one installation.
- **Source.** The pydantic models stay the single source. `casebench schema export` writes each format to `schemas/<name>/v<major>.json`, as JSON Schema Draft 2020-12, the draft pydantic generates. Each schema carries a `$id` under the project's documentation site. The schemas are committed and attached to every release.
- **Version.** A format's version is `<major>.<minor>`, separate from the package version. A file declares it once, never on each line: `report.json`, a profile and a suite manifest carry `"format": "casebench.report/1.0"` (and so on). The manifest also names the case format of its lines, and a profile names the document format its connector returns.
- **Compatibility.** Within a major version, a change may only add optional fields or enum values; it never removes, renames, narrows or makes a field required. A new major version is a breaking change, and Casebench keeps reading the previous major version for at least one more major release.
- **Reading a file.** Records reject unknown fields, so a typo in a hand-written file fails loudly. That rule stays for every file at a version this Casebench knows. For other versions:
  - a file at a newer minor version is read with its unknown fields ignored, and a warning names them;
  - a file at a newer major version is refused, with the version Casebench supports.
- **Extensions.** Anything outside a format goes under `extensions`, keyed by a domain the author controls (`"extensions": {"example.com": {...}}`). It is never required and never read by the core. `ee/` uses it like anyone else, so no public format depends on `ee/`.
- **Drift and growth.** A test regenerates every schema and fails when the committed file differs. A second test compares each schema with the last released one of the same major version and fails on any change the compatibility rule forbids.
- **Results elsewhere.** Casebench defines no general results format. An exporter writes reports to [Every Eval Ever](https://github.com/evaleval/every_eval_ever), the EvalEval Coalition's community-governed results schema. It is built only once that schema is shown to keep results split by task, metric and reference source (rule 8), and it runs only when the user asks: Casebench publishes nothing itself.
- **Name and licence.** These are "Casebench formats" in the docs. The schemas are Apache-2.0 like the rest of the core, whose patent grant covers contributors' changes.

### Consequences

- Good, because anyone can validate a document, a case or a report in any language without running Casebench, and can rely on a major version not breaking.
- Good, because the code and the published shape cannot disagree: the test fails first.
- Bad, because every model change to these formats now needs a compatibility review, and a breaking one needs a new major version and a reader for the old one.
- Bad, because a pydantic upgrade that changes the generated schema shows up as drift, even when the format has not changed.

## Why not the others

- Written specification first: it needs a working group and implementers to justify it, and with neither it is a second copy of the code that drifts.
- Existing formats for everything: no published format holds a legal test case with its evidence and source decision; transport (MCP, HTTP) and results (Every Eval Ever) are already adopted where they fit.
- Publish nothing yet: no outsider builds on a shape that can break in any minor release, so the second organisation never comes.

## Revisit when

- A second organisation implements a format and wants a say in changing it. A written specification, its licence (such as the Community Specification License) and its governance are decided then.
- Every Eval Ever is checked: the exporter is built if it keeps per-source results apart, and recorded as not possible if it does not.

## More information

Checked on 2026-10-13:

- [pydantic](https://pydantic.dev/docs/validation/latest/concepts/json_schema/) 2.14 (the version in `uv.lock`) generates schemas compliant with JSON Schema Draft 2020-12.
- Casebench's records forbid extra fields (`casebench/core/model.py`); no file it writes declares a format version.
- [Every Eval Ever](https://arxiv.org/pdf/2606.14516) (MIT licence) holds an array of evaluation results with uncertainty, and a `schema_version`. Whether one result can carry a breakdown such as a reference source has not been checked.
- [Inspect](https://inspect.aisi.org.uk/eval-logs.html) publishes its log schema from code (`inspect log schema`), the same approach as this record.
- `docs/design/open-source.md` already plans a versioned run-log format with a published schema and an Every Eval Ever exporter.
