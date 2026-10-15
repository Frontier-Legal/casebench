# Working on Casebench

Casebench measures the legal accuracy of an AI system against real court decisions and lawyer-written references, in any jurisdiction. This file is the contract for anyone, person or tool, who changes the code. CONTRIBUTING.md covers the mechanics of a pull request; `docs/decisions/` holds the reasons behind the design.

## Layout

- `casebench/` is the core package: the evaluation case model, runners, metrics, the command line and the local workbench.
- Casebench has no country-specific code. Models extract answer keys and citations, and the corpus resolves citations to documents (decision 0024).
- Corpus connectors, capture parsers, model providers and the other plugin kinds are plugins, discovered through entry points, each kind with an interface and a conformance suite defined in the core. Built-in plugins register in the core's own `pyproject.toml`; a third-party plugin is its own package named `casebench-<name>`.
- `docs/design/` describes the system; `docs/decisions/` records why, one MADR file per decision.
- `ee/` is under the Elastic License 2.0 and everything else under Apache-2.0; `LICENSE` names the boundary. `ee/` is packaged on its own and plugs into the core through entry points. The core never imports from `ee/`. Every source file under `ee/` starts with `SPDX-License-Identifier: Elastic-2.0`.

## Rules

1. One file has one job. The first line of its module docstring names that job in one sentence, and everything in the file serves it. When a change adds code that serves a different job, that code goes in its own file. A reviewer who cannot say the job without "and" asks for a split; a test checks that every module states its job.
2. A change to behaviour arrives with a test that fails before the change and passes after it. Name the test after what a user would notice. A behaviour written as a scenario gets exactly one test named after that scenario.
3. No magic numbers. A budget, limit or timeout is derived from a documented contract or from a measurement, and the decision record says which, with the date.
4. Identifiers are English. Other languages appear only in user-facing strings and test fixtures.
5. Nothing leaves the user's machine except calls to the system under test and the judge the user configured. There is no telemetry.
6. Metrics read the corpus. They never ask the system under test to verify itself, and a human verdict always outranks a model's.
7. A material choice, such as a dependency, a public interface or a storage format, gets a decision record under `docs/decisions/` before the code.
8. Results are reported per task, per metric and per reference source. There is no single accuracy number, and the project publishes no rankings of products.

## Commits and releases

- Commit messages follow [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, with a scope when it helps, as in `feat(sdk): ...`. A breaking change carries `!` and a `BREAKING CHANGE:` footer.
- Versions follow [SemVer](https://semver.org/). While the version is 0.x, a minor release may break. The version and `CHANGELOG.md` are generated from the commits at release time.
- Every commit is signed off (`git commit -s`), which is the Developer Certificate of Origin.
- Pull requests target `main` and merge with green CI and a review.

## Checks

```
uv sync
uv run pytest
uv run ruff check .
uv run pyright
pre-commit run --all-files
```

Run the tests for the area you changed before opening a pull request, and the whole suite before a release.

## Out of scope

- Production observability: traces exist only to explain evaluation results.
- Shipping any corpus. Users connect their own decisions and statutes.
- Grading drafting or advice without an evidenced reference.
