# Casebench open-source standards and adoption

## Repository standards (checked 2026-09-29)

| Item | Choice | Source |
|---|---|---|
| Licence | open core: Apache-2.0 for the core (SDK, CLI, metrics, plugins, local UI, report, spreadsheet round-trips); `ee/` (roles, SSO, audit, invites, the push/pull server side) source-available, free for your own organisation, no offering to third parties. The whole project under FSL or ELv2 was rejected: vendors will not adopt a yardstick they cannot fork, and adapter contributors will not build for a product someone else owns | [decision 0004](../decisions/0004-open-core-and-ee-boundary.md) |
| Trademark | a trademark policy: forks may not be called Casebench. Apache-2.0 grants no rights to the name | |
| Contributions | DCO via the [DCO app](https://github.com/apps/dco), `git commit -s` for the core; a CLA only for `ee/` | DCO is lighter for firm and vendor engineers; the CLA keeps `ee/` relicensable |
| Code of conduct | [Contributor Covenant 3.0](https://www.contributor-covenant.org/version/3/0/) (Jul 2025) | |
| Security policy | `SECURITY.md` pointing to [GitHub private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/working-with-repository-security-advisories/configuring-private-vulnerability-reporting-for-a-repository); 14-day first response | [Best Practices criteria](https://www.bestpractices.dev/en/criteria/0) |
| Commits and changelog | [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/); release tooling generates the version and CHANGELOG.md from them (default release-please) | |
| Agent contract | public `AGENTS.md`, the contract for anyone, person or tool, who changes the code | |
| Versioning | [SemVer](https://semver.org/); 0.x may break, stated in the README | |
| Citation | `CITATION.cff` 1.2.0 (GitHub "Cite this repository", Zenodo DOI) | [CFF](https://citation-file-format.github.io/) |
| Branch rules | [rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets): review and green CI on `main`; [push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection) for secrets | |
| Supply-chain score | [OpenSSF Scorecard](https://github.com/ossf/scorecard/blob/main/docs/checks.md) action: Actions pinned by SHA, least-privilege tokens, Dependabot (uv supported since [Mar 2025](https://github.blog/changelog/2025-03-13-dependabot-version-updates-now-support-uv-in-general-availability/)), SAST, [zizmor](https://docs.zizmor.sh/) for workflows | |
| Governance | `GOVERNANCE.md` and `MAINTAINERS` once a second organisation maintains code; neutrality terms published at R1 | |
| Later | [Best Practices badge](https://www.bestpractices.dev/), [OSPS Baseline](https://baseline.openssf.org/), [REUSE 3.3](https://reuse.software/spec-3.3/) headers | |

Community files at R1: README, LICENSE, AGENTS.md, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG, CITATION.cff, issue and PR templates, `PLUGINS.md` (how to add a data provider or model API).

## Packaging and release

| Item | Choice |
|---|---|
| Build | PEP 621 `pyproject.toml`, [`uv_build`](https://docs.astral.sh/uv/concepts/build-backend/) backend (pure Python), `py.typed` shipped |
| Python | 3.11 to 3.14 at R1, then [SPEC 0](https://scientific-python.org/specs/spec-0000/) with a lag, because firm environments trail |
| Quality gates | pre-commit, ruff, pyright, pytest on Linux, macOS and Windows |
| Publish | [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) through `pypa/gh-action-pypi-publish`, which [attests by default](https://docs.pypi.org/attestations/producing-attestations/); build and publish in separate jobs; `id-token: write` only on publish. `uv publish` alone does not generate attestations |
| Later | [immutable releases](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases), SBOM in the wheel ([PEP 770](https://peps.python.org/pep-0770/)), SLSA provenance |
| Plugins | [entry points](https://packaging.python.org/en/latest/specifications/entry-points/) per plugin kind ([architecture.md](architecture.md)), the [pytest](https://docs.pytest.org/en/stable/how-to/writing_plugins.html) and [Inspect](https://inspect.aisi.org.uk/extensions.html) pattern; `casebench-<name>` naming for third-party packages, built-in jurisdictions inside the core ([decision 0013](../decisions/0013-built-in-jurisdictions-load-on-demand.md)); `casebench plugin new` scaffolds a kind and `casebench plugin test` runs its conformance suite |

## First-run path

| Minute | Command | What the user sees |
|---|---|---|
| 0 | `uvx casebench demo` | a bundled sample (a lawyer-authored mini set, a few public decisions, an echo target, cached judge verdicts) runs with no key; the viewer opens on real failures |
| 2 | `casebench init`, or "set up Casebench for this agent" to a coding agent with the repo's skill | the stack detected from the repo and lockfile (SDKs, vector store, reranker); two questions, where the corpus is and which judge; `casebench.yaml` written with its `# yaml-language-server: $schema=` line, the proxy's environment lines printed, one sample case sent and its parsed answer and citations shown |
| 5 | `casebench run` | on first use: extraction, generation, a cost estimate and a confirmation; then the run with live progress, resumable; a link to the workbench |
| 10 | `casebench ui` | the workbench: failures beside evidence, ready for a lawyer to review; the harness waterfall and the authority funnel for engineers |
| 15 | `casebench push`, then `casebench invite ayse@firm.com --role reviewer` | the run and its cases are in Casebench Cloud; the lawyer gets an email naming the items and the time they take, logs in from the link, Microsoft or Google, and lands in the queue; `casebench pull` later brings approvals back for CI |
| 20 | `casebench export --review` | the same review as an XLSX for a lawyer with no login and no cloud; `casebench import` merges their verdicts |
| later | GitHub Action | a PR comment with per-metric before/after and significance, the pattern of [promptfoo's action](https://www.promptfoo.dev/docs/integrations/github-action/) |

Choices behind it:

- **Three commands, everything else a flag.** `init`, `run` and `ui` are the whole surface for most users. `corpus check`, `target check`, `extract`, `generate` and `--dry-run` stay as power-user subcommands that `init` and `run` call for everyone else. The same flow ships as a `SKILL.md` in the Agent Skills format.
- **Lawyers never touch YAML.** `casebench template lawyer --task qa|drafting|editing` writes an XLSX/CSV with columns for facts, question, reference answer, key points, weights and authorities; `casebench import` turns it into cases. Firms' ground truth lives in spreadsheets and Word files already. The same shape carries reviews back (`casebench export --review`), so a lawyer with no login still takes part.
- **YAML and Python are equal citizens.** Config is YAML with a published JSON Schema; the same objects are importable in Python and in pytest.
- **One app for engineers and lawyers.** `casebench ui` binds to 127.0.0.1 with no login. The same app is Casebench Cloud, and self-hosts as a team server for firms that cannot push ([workbench.md](workbench.md)). A static report export covers sharing with people who have no access.
- Later, an MCP server so coding agents can run suites ([promptfoo mcp](https://www.promptfoo.dev/docs/integrations/mcp-server/) precedent), and notebook display helpers.
- Maintainers of comparable tools publish adoption numbers, not causes ([Langfuse](https://langfuse.com/handbook/chapters/open-source) credits self-hosting and no lock-in). The path above is inference from their patterns, to be measured by the R1 gate ([releases.md](releases.md)).

## Data interoperability

- Suites: JSONL, one case per line, stable `id`; publishable to the Hugging Face Hub with a [dataset card](https://huggingface.co/docs/hub/datasets-cards) (Croissant metadata comes free).
- Run logs: a versioned JSON format with a published schema, as [`inspect log schema`](https://inspect.aisi.org.uk/eval-logs.html) does. Exporter to [Every Eval Ever](https://github.com/evaleval/every_eval_ever) later.

## Security rules

| Risk | Rule |
|---|---|
| API keys | read from environment or keyring only; never written to config, logs or run logs; auth headers redacted |
| Untrusted model output | never `eval`, `exec` or unpickle outputs; `yaml.safe_load` only; the viewer HTML-escapes everything under a strict CSP ([OWASP LLM05](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)) |
| Egress | per-target host allowlist; cross-host redirects refused; default timeouts |
| Custom Python metrics | run in-process at R1 with a warning; container sandbox with no network later ([Inspect sandboxing](https://inspect.aisi.org.uk/sandboxing.html)) |
| Team server and cloud | no default password; first admin set at setup; OIDC for firm SSO; API keys for CI; the cloud isolates tenants per organisation and holds only what push sends ([workbench.md](workbench.md)) |
| Telemetry | none in v0.x ([decision 0007](../decisions/0007-no-telemetry.md)). [promptfoo](https://github.com/promptfoo/promptfoo/issues/9968) and [DeepEval](https://github.com/confident-ai/deepeval/issues/2497) both have open issues over theirs, and firm security reviews check for it |
