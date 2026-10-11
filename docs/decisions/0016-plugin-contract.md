---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Plugins: entry points, a manifest, conformance figures and explicit sources

Amended by [0024](0024-no-jurisdiction-adapters.md): the adapter kind is removed.

## Context and problem statement

A contributor in any country must be able to add their courts, their data provider, their model provider or a parser for their backend without changing the core or asking the maintainers. Plugins may be built into the core ([0013](0013-built-in-jurisdictions-load-on-demand.md)) or published as `casebench-<name>` packages. Both need the same discovery, the same contract and the same proof that they work.

## Considered options

- Python entry points per plugin kind, a small manifest in each plugin folder, a conformance suite per kind that reports measured figures, and explicit sources on name clashes
- pluggy hooks, as pytest uses
- A plugin directory scanned for modules
- Plugins named in the config by import path only

## Decision outcome

Chosen option: "entry points, a manifest, conformance figures, explicit sources".

- **Discovery.** Each kind has one entry-point group: `casebench.adapters`, `casebench.corpus`, `casebench.capture`, `casebench.providers`, `casebench.tasks`, `casebench.references`, `casebench.targets`, `casebench.metrics`, `casebench.exporters`. An entry point is loaded only when a config selects its name, so an installed plugin costs nothing until used. Built-in plugins register in the core's own `pyproject.toml`.
- **Contract.** Each kind's interface is a `typing.Protocol` in the core. pluggy's many-implementations-per-hook model fits pytest's event hooks; Casebench needs one named implementation per config entry, which entry points give directly.
- **Manifest.** Every plugin folder, built in or packaged, holds `casebench-plugin.json` with its kind, its name and the object that implements the interface. `casebench plugin test <path>` reads it, so the command works on a folder inside the core and on a separate package alike.
- **Conformance.** Each kind has a conformance suite that runs on the plugin's own samples in its `samples/` folder. Passing means the plugin meets its interface on every sample. The suite also measures a figure (extraction accuracy for an adapter, fields covered for a connector, calls parsed for a parser, responses parsed for a provider) and reports it beside the pass. There is no pass threshold on the figure: the project has no measurement yet that would justify one, and a reader can judge a published figure.
- **Model providers are pure.** A provider turns messages into an HTTP request and an HTTP response into a completion. The core sends the request. A provider's conformance therefore runs offline on recorded exchanges, and the core's network allowlist applies to every provider.
- **Clashes.** When two installed distributions register the same name in one group, nothing is chosen silently. The config must name the distribution (`source`), and the error says how.
- **Boundary.** Framework code never imports a plugin module; only the registry loads one, by the name in the config. A test enforces this.

### Consequences

- Good, because a built-in plugin and a third-party one are found, tested and listed the same way.
- Good, because a provider for a national model API needs no change to the core and no network to test.
- Bad, because the manifest duplicates what the entry point says; the conformance command checks that they agree.

## Revisit when

A plugin kind needs more than one implementation active at once (event hooks, say), which pluggy handles better, or the figures gain a measured threshold that should gate listing.

## More information

- [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
- [Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- [pluggy](https://pluggy.readthedocs.io/)
