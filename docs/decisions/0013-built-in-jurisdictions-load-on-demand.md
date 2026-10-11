---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Built-in jurisdictions ship in the core and load on demand

Supersedes [0006](0006-every-adapter-is-its-own-package.md).

## Context and problem statement

Decision 0006 shipped every jurisdiction adapter as its own distribution, Türkiye included, to keep the core free of country logic. A firm or vendor that works in several jurisdictions would then track one package and one version per country, and the project would run one PyPI project, one release line and one trusted publisher per country while it has a single maintainer. The boundary 0006 protected is an architectural one: framework code must not depend on a country. A separate distribution is one way to enforce it, not the only one.

## Considered options

- Built-in jurisdictions inside the core distribution, under `casebench/jurisdictions/<code>/`, loaded through the same entry-point registry that third-party adapters use
- Separate distributions per country, with core extras that pull them in (`casebench[tr]` depends on `casebench-tr`)
- Separate distributions per country with no extras (decision 0006)

## Decision outcome

Chosen option: "Built-in jurisdictions inside the core, loaded on demand", because users get one package and one version whatever jurisdictions they need, the project keeps one release line, and nothing country-specific is imported until a config selects it. spaCy ships its languages the same way (`spacy.lang.<code>`).

- Each built-in jurisdiction lives in `casebench/jurisdictions/<code>/` and is registered by the core's own `pyproject.toml` under the adapters entry-point group. Entry points import their target only when loaded, so a jurisdiction no config names is never imported.
- A jurisdiction that needs heavy dependencies declares them as an extra named after its code, such as `casebench[tr]`. Without the extra, selecting it fails with a message naming the extra.
- Framework code (everything outside `casebench/jurisdictions/`) never imports a jurisdiction module. Only the registry loads one, by the name in the config. A test enforces this.
- Third parties can still publish `casebench-<code>` packages registering the same entry point, with no pull request to this repository. When a built-in and a third-party adapter claim the same code, the config must say which one it means.
- Every adapter, built-in or third-party, passes the same conformance suite.
- Lawyer-authored cases still work in any country with no adapter; court-derived references and citation checks need the country's adapter.

This also replaces the `packages/` workspace layout for adapters in [0009](0009-packaging-and-python-versions.md).

### Consequences

- Good, because a multi-jurisdiction team installs one package and upgrades one version.
- Good, because the project publishes and attests one distribution.
- Good, because a jurisdiction's code is still isolated in its own folder, with its own conformance samples and CODEOWNERS entry.
- Bad, because a fix to one country's parser ships as a core release, and the core's release notes carry country changes.
- Bad, because contributors who want a jurisdiction maintained in this repository need a maintainer's review; the third-party route stays open for those who do not.

## Revisit when

A jurisdiction's maintainers want their own release cadence, the core's install size grows noticeably from country data, or country-specific changes dominate the core's releases.

## More information

- [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
- [spaCy language data](https://spacy.io/usage/linguistic-features#language-data)
