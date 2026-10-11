---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Every jurisdiction adapter is its own package

## Context and problem statement

Court-derived references and citation checks depend on a country's citation formats, decision layout, court hierarchy and statute versions. If the first country's adapter lives inside the core, the core is that country's tool with a plugin system attached, and a contributor elsewhere has no clean example of what an adapter is.

## Considered options

- The core holds the adapter interface and its conformance suite; each country ships as its own distribution, Türkiye included
- Adapters as subpackages of the core
- One adapters package holding every country

## Decision outcome

Chosen option: "Each country ships as its own distribution", because the core then contains no jurisdiction, and the first adapter is a reference a contributor can copy.

The core discovers adapters through Python entry points and never imports one by name. Türkiye ships as `casebench-tr`. For now it is a workspace member under `packages/casebench-tr/` in this repository, published as its own distribution; it moves to its own repository when a second country's maintainers exist. Lawyer-authored cases work in any country with no adapter; court-derived references and citation checks need the country's adapter.

### Consequences

- Good, because the "no country in the core" rule is checkable: a search of the core for jurisdiction names and citation formats finds none outside demo data.
- Good, because each adapter has its own owners, releases and conformance figures.
- Bad, because two distributions release from one repository until the adapter moves out.

## Revisit when

A second jurisdiction's maintainers want their own repository, or the adapter interface has to change in a way that breaks every adapter at once.

## More information

- [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
- The pytest plugin model (`pytest-<name>` packages registering entry points) is the pattern.
