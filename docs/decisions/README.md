# Architecture decision records

Every material choice in Casebench has a record here: a dependency, a public interface, a storage format, a licence boundary. The record lands before or with the code that follows it, in the same pull request.

## Rules

- One decision per file, named `NNNN-short-title.md`, numbered in order. Numbers are never reused.
- The format is [MADR 4](https://adr.github.io/madr/). Copy [template.md](template.md).
- Every record has a status, the context, the options weighed, the decision, its consequences and a "Revisit when" section.
- A reversed decision is never deleted or rewritten. The new record says which one it supersedes; the old one gets `status: superseded by NNNN` and a link forward.
- A budget, limit or timeout in the code names its source here: a documented contract or a measurement, with the date.

## Records

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions in MADR 4 | accepted |
| [0002](0002-evaluation-case-model.md) | The evaluation case is the unit: task, reference, metrics | accepted |
| [0003](0003-opentelemetry-genai-trace-model.md) | OpenTelemetry GenAI conventions are the trace model | accepted |
| [0004](0004-open-core-and-ee-boundary.md) | Open core: Apache-2.0 everywhere except `ee/` | accepted |
| [0005](0005-cloud-never-computes-a-score.md) | A shared server never computes a score | accepted |
| [0006](0006-every-adapter-is-its-own-package.md) | Every jurisdiction adapter is its own package | accepted |
| [0007](0007-no-telemetry.md) | No telemetry | accepted |
| [0008](0008-zero-code-capture-before-decorators.md) | Zero-code capture before decorators | accepted |
| [0009](0009-packaging-and-python-versions.md) | uv workspace, `uv_build`, Python 3.11 to 3.14 | accepted |
| [0010](0010-releases-from-conventional-commits.md) | Versions and changelog come from Conventional Commits | accepted |
| [0011](0011-ci-and-supply-chain.md) | One set of checks, locally and in CI, with a pinned supply chain | accepted |
