# Casebench formats

Casebench publishes the shapes other tools read and write as JSON Schemas, each with its own version ([decision 0034](../decisions/0034-versioned-formats.md)). This page lists them, says where a file names its version, and lists the rules a schema cannot hold.

## The formats

| Format | What it is | Where a file names its version |
|---|---|---|
| `casebench.document/1.0` | one court decision or statute, as a corpus connector returns it | outside the file: the provider's profile, or `--format` |
| `casebench.case/1.0` | one evaluation case, one line of `suite.jsonl` | the suite's `manifest.json`, as `case_format` |
| `casebench.suite/1.0` | a frozen suite's `manifest.json` | its own `format` field |
| `casebench.report/1.0` | a scored run's `report.json` | its own `format` field |
| `casebench.profile/1.0` | a data provider's profile, in YAML ([decision 0033](../decisions/0033-data-provider-profiles.md)) | its own `format` field |

The schemas ship with Casebench under `casebench/formats/schemas/<name>/<major>.<minor>.json`. `casebench schema export --into DIR` writes a copy. They are not yet published at a stable address: that waits for the project's own domain.

## Checking a file

```
casebench validate report.json
casebench validate suite/suite.jsonl
casebench validate decision.json --format casebench.document/1.0
```

`validate` checks the schema and the rules below together, and names every problem with where it is.

A file at a version Casebench knows is read strictly: an unknown field is an error, so a typo fails loudly. A file at a newer minor version is read with its unknown fields ignored, and they are named. A file at another major version is refused.

## Rules a schema cannot hold

| Format | Rule |
|---|---|
| case | Every fact id within a reference is unique. |
| case | A criterion's weight is never zero. |
| case | A criterion with a positive weight is derived from at least one fact; every fact it names exists. |
| suite | The cases in `suite.jsonl`, read in order, hash to the manifest's `content_hash`. |

The schema describes the canonical form only. Casebench also accepts `derived_from` for a criterion's `from`, but writes `from`.

## Extensions

Data outside a format goes under `extensions`, keyed by a domain its author controls:

```json
"extensions": {"example.com": {"reviewed_in": "2024-Q3"}}
```

Casebench never reads it and never requires it.
