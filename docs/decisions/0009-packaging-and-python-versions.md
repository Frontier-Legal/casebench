---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# uv workspace, `uv_build`, Python 3.11 to 3.14

## Context and problem statement

The core and the first adapter are separate distributions that live in one repository for now. Contributors need one command to get a working environment, and firm environments trail the newest Python by a year or more.

## Considered options

- A uv workspace with the `uv_build` backend, PEP 621 metadata, `uv.lock` committed
- Hatchling or setuptools with pip and a requirements file
- Poetry

## Decision outcome

Chosen option: "A uv workspace with `uv_build`", because `uv sync` builds the whole workspace from a committed lockfile, `uv_build` is a pure-Python backend with no extra build dependency, and the same tool runs the checks and builds the release.

- The core package is `casebench/` at the repository root. Adapters and other first-party plugins are workspace members under `packages/`.
- Every distribution ships `py.typed`.
- Supported Python versions are 3.11 to 3.14. After the first public release the floor follows [SPEC 0](https://scientific-python.org/specs/spec-0000/) with a lag of one minor version, because firm environments trail.
- The core depends on as little as it can; integrations come as extras named after the user's library, never after the vendor that instruments it.

### Consequences

- Good, because `uv sync` and `uv run pytest` are the whole setup for a contributor.
- Good, because the lockfile makes CI and local runs use the same versions.
- Bad, because contributors who do not use uv need to read the lockfile through `uv export` or install from PyPI metadata.

## Revisit when

`uv_build` stops covering a need the project has (compiled extensions, for one), or Python 3.11 reaches end of life (October 2027).

## More information

- [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/)
- [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [Python release status](https://devguide.python.org/versions/)
