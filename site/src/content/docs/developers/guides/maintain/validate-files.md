---
title: Validate a file
description: Check a suite, a report, a document or a provider profile against its published JSON Schema and the rules a schema cannot hold, and check casebench.yaml in your editor.
sidebar:
  order: 3
---

Every file Casebench reads or writes for other tools has a versioned format with a JSON Schema. `validate` checks a file against its format and against the rules a schema cannot express, and names every problem with where it is.

```sh
casebench validate suites/employment/suite.jsonl
casebench validate suites/employment/manifest.json
casebench validate .casebench/runs/court-1/report.json
casebench validate acme-legal.yaml
casebench validate decisions/ewca-civ-2025-0412.json --format casebench.document/1.0
```

A suite manifest, a report and a profile name their own format. The lines of `suite.jsonl` take the case format their manifest names. A document names none, so give `--format`, and give it for a case outside a suite too, such as `--format casebench.case/1.1`.

A valid file prints one line, such as:

```text
suites/employment/suite.jsonl: valid casebench.case/1.1, 7 record(s)
```

A file with problems prints each one and exits with status 1:

```text
case.json: provenance.jurisdiction: Value error, 'XX' is not a jurisdiction code; write ISO 3166-1 alpha-2 such as NO or TR, ISO 3166-2 such as US-CA, or EU
Error: case.json is not valid casebench.case/1.1
```

## How versions are read

- A file at a version Casebench knows is read strictly: an unknown field is an error, so a typo fails loudly.
- A file at a newer minor version is read with its unknown fields ignored, and they are named.
- A file at another major version is refused.

## Rules a schema cannot hold

| Format | Rule |
| --- | --- |
| case | Every fact id within a reference is unique. |
| case | A criterion's weight is never zero. |
| case | A criterion with a positive weight comes from at least one fact, and every fact it names exists. |
| suite | The cases in `suite.jsonl`, read in order, hash to the manifest's `content_hash`. It is checked when the two files sit side by side. |
| case, profile | A jurisdiction is an ISO 3166-1 alpha-2 code, an ISO 3166-2 code or `EU`. `UK` and `EL` are read as `GB` and `GR`. |

Casebench writes every document id with its corpus's name, as `<corpus>:<id>`. `validate` accepts an id without one, which a setup with one corpus reads as that corpus's.

## Get the schemas for other tools

```sh
casebench schema export --into schemas/
```

It writes each format's schema at its current version, one folder per format: `case/1.1.json`, `suite/1.0.json`, `report/1.1.json`, `document/1.0.json` and `profile/1.0.json`. Point your editor's JSON or YAML schema setting at them for completion and inline errors.

## Check casebench.yaml in your editor

`casebench.yaml` is not one of these formats, and `validate` does not read it. Every command checks it when it loads it, and stops with every problem and where it is. For checks as you type, `casebench init` writes `.casebench/casebench.schema.json` and starts the file with the line an editor with YAML language support reads:

```yaml
# yaml-language-server: $schema=.casebench/casebench.schema.json
```

See [Validate in your editor](/developers/reference/configuration/#validate-in-your-editor).

## Related

- [File formats](/developers/reference/formats/), generated from the same schemas.
