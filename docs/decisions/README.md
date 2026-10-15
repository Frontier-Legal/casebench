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
| [0006](0006-every-adapter-is-its-own-package.md) | Every jurisdiction adapter is its own package | superseded by [0013](0013-built-in-jurisdictions-load-on-demand.md) |
| [0007](0007-no-telemetry.md) | No telemetry | accepted |
| [0008](0008-zero-code-capture-before-decorators.md) | Zero-code capture before decorators | accepted |
| [0009](0009-packaging-and-python-versions.md) | uv workspace, `uv_build`, Python 3.11 to 3.14 | accepted |
| [0010](0010-releases-from-conventional-commits.md) | Versions and changelog come from Conventional Commits | accepted |
| [0011](0011-ci-and-supply-chain.md) | One set of checks, locally and in CI, with a pinned supply chain | accepted |
| [0012](0012-click-for-the-command-line.md) | Click for the command line | accepted |
| [0013](0013-built-in-jurisdictions-load-on-demand.md) | Built-in jurisdictions ship in the core and load on demand | superseded by [0024](0024-no-jurisdiction-adapters.md) |
| [0014](0014-pydantic-for-the-data-model.md) | Pydantic for the data model | accepted |
| [0015](0015-suite-and-run-log-formats.md) | Suites and run logs are JSON Lines with a manifest | accepted |
| [0016](0016-plugin-contract.md) | Plugins: entry points, a manifest, conformance figures and explicit sources | accepted |
| [0017](0017-target-contract.md) | A target is a Python entry point, an HTTP endpoint or a command | accepted |
| [0018](0018-httpx-jsonpath-ng-and-pyyaml.md) | httpx, jsonpath-ng and PyYAML | accepted |
| [0019](0019-recording-proxy.md) | A recording proxy captures model and backend calls from any language | accepted |
| [0020](0020-python-process-wrapper.md) | Python agents run in worker processes, one per parallel slot | accepted |
| [0021](0021-httpx2.md) | httpx2 for Casebench's own HTTP calls | accepted |
| [0022](0022-config-named-functions.md) | A function named in the config is wrapped when the agent's process starts | accepted |
| [0023](0023-otlp-trace-intake.md) | Traces a team already emits are received over OTLP and joined to cases | accepted |
| [0024](0024-no-jurisdiction-adapters.md) | No jurisdiction adapters: the corpus resolves citations and models extract | accepted |
| [0025](0025-corpus-connectors.md) | Corpus connectors fetch, search and are cached; any store is configured, not coded | accepted |
| [0026](0026-judge-and-citation-checks.md) | The judge lists, matches and weighs citations; the corpus finds them | accepted |
| [0027](0027-answer-keys-from-decisions.md) | Two models extract each answer key; a field counts only where their quotes agree | accepted |
| [0028](0028-scores-baselines-and-intervals.md) | Scores carry a bootstrap interval and a baseline; outcome scores need no model | accepted |
| [0029](0029-statute-and-precedent-scores.md) | Statute and precedent scores compare corpus documents; the judge's replies stay with the run | accepted |
| [0030](0030-set-up-here-run-there.md) | Set up where the code is; check and run where the agent and the corpus are reachable | accepted |
| [0031](0031-authority-funnel.md) | The authority funnel follows each court authority through the captured steps | accepted |
| [0032](0032-provider-catalog-and-sdk-providers.md) | Models are picked from a public catalog; cloud providers are called through the project's own SDK | accepted |
| [0033](0033-data-provider-profiles.md) | Data providers are profiles the built-in connectors run; a code plugin only where a profile cannot reach | accepted |
| [0034](0034-versioned-formats.md) | Casebench formats are versioned JSON Schemas generated from the models | accepted |
| [0035](0035-comparable-and-strict-scores.md) | Every score set says what produced it; a strict pass rate and a second judge are reported beside the scores, never blended | accepted |
| [0036](0036-several-corpora.md) | A setup connects several corpora by name; citations go to the corpus that covers their jurisdiction | accepted |
| [0037](0037-match-by-the-corpus-description.md) | The judge matches citations by what the corpus says about each result, one call per answer; scoring runs in parallel and survives a dropped call | accepted |
| [0038](0038-model-settings-by-measurement.md) | Each model takes its provider's own settings, and a team picks them from measured agreement, time and cost | accepted |
| [0039](0039-one-case-by-a-lawyer.md) | A lawyer writes one case at a time, from a decision found by topic or by hand, and approves it | accepted |
| [0040](0040-init-reads-the-code.md) | Init reads the project's own code, offline, to find its model clients, model names and entry points | accepted |
| [0041](0041-a-profile-says-what-may-be-kept.md) | A profile says what a provider's terms let Casebench keep on disk, and the cache follows it | accepted |
| [0042](0042-upgrade-in-place.md) | An existing setup upgrades in place: init updates the config, old files are read as they are, caches carry over | accepted |
| [0043](0043-guided-onboarding.md) | Onboarding detects first, asks last, and finds keys in the project's .env files; Rich draws it | accepted |
| [0044](0044-onboarding-by-a-coding-agent.md) | A coding agent sets Casebench up from one prompt, and only casebench.yaml and .casebench/ change | accepted |
| [0045](0045-setup-spends-little.md) | Setup spends one search and one document, and greets the agent once | accepted |
| [0046](0046-the-perimeter.md) | A run calls only the hosts its config names, never follows a redirect to another host, and writes no key | accepted |
| [0047](0047-the-judge-rests-on-evidence.md) | A verdict rests on a quote the answer holds and on the case's evidence, and lawyers' verdicts calibrate the judge | accepted |
| [0048](0048-a-gate-in-ci.md) | A gate fails a build only on a significant drop, over approved cases, against a saved baseline | accepted |
| [0049](0049-lawyers-write-cases-in-a-spreadsheet.md) | Lawyers write cases in a spreadsheet, and research, drafting, editing and extraction tasks are graded | accepted |
| [0050](0050-the-review-queue.md) | The review queue: run folders stay the truth, a database keeps what people do, and one web app serves lawyers and engineers | accepted |
| [0051](0051-what-a-run-spends.md) | A run reports what it spent, per model, for the agent and for the judge | accepted |
| [0052](0052-golden-data-needs-a-second-editor.md) | Golden data changes only when a second editor approves, and a question can be tried within a daily dollar limit | accepted |
