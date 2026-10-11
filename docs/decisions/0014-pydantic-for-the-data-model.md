---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Pydantic for the data model

## Context and problem statement

Cases, references, scores, manifests and run-log records cross every boundary in Casebench. They are written to disk and read back by another version, edited by hand, imported from spreadsheets and returned by user code. They need validation with errors that name the field, a stable JSON form, and a JSON Schema so editors can autocomplete suite and config files.

## Considered options

- Pydantic v2 models
- Standard-library dataclasses with hand-written validation and schema
- attrs with cattrs
- msgspec

## Decision outcome

Chosen option: "Pydantic v2", because one class gives validation on load, JSON serialisation and the JSON Schema, and it is the validation library most Python contributors already know.

- Models reject unknown fields, so a typo in a hand-written case fails loudly instead of being dropped.
- Records that are append-only once written (scores, manifests, results) are frozen.
- What goes to disk is the model's own `model_dump(mode="json")`. Content hashes are taken over a canonical form of that JSON ([0015](0015-suite-and-run-log-formats.md)), never over Python objects.

### Consequences

- Good, because user code can build cases in Python with type checking and get the same validation as files.
- Good, because the JSON Schema for editors comes from the same classes, so it cannot drift.
- Bad, because Pydantic depends on a compiled package (`pydantic-core`). Wheels exist for every platform and Python version Casebench supports.

## Revisit when

A Pydantic release changes serialisation in a way that alters stored files, or install size becomes a reason users give for not adopting Casebench.

## More information

- [Pydantic](https://docs.pydantic.dev/)
- [JSON Schema generation](https://docs.pydantic.dev/latest/concepts/json_schema/)
