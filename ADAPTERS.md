# Adding a jurisdiction

Lawyer-authored cases work in any country with no adapter. Court-derived references and citation checks need an adapter for the country: a package that knows how its courts write decisions and cite law.

## What an adapter does

- Parses the country's citation formats for decisions and statutes.
- Finds the operative part of a decision, so facts can end before the ruling.
- Maps courts to levels, so a suite can be stratified by court.
- Optionally, looks up the version of a statute article in force on a date.

The adapter reads decisions; it never fetches them. Where decisions come from is a corpus connector's job, and the two are bound per corpus in `casebench.yaml`. One connector can serve several countries.

## Steps

1. Scaffold a package: `casebench plugin new adapter --name <country>`. It writes `casebench-<country>` with the interface stubs, a conformance test and a README.
2. Add sample decisions and the extractions a person checked by hand, in the package's `samples/` folder. Use decisions you are allowed to redistribute.
3. Implement the interface until `casebench plugin test ./casebench-<country>` passes. It checks citation parsing, operative-part extraction and statute lookup against your samples and prints your measured extraction accuracy.
4. Publish the package to PyPI under the name `casebench-<country>`. The core finds it through its entry point; nothing in the core changes.
5. Open an issue with the "A new jurisdiction" template so the README can list it with its measured figures.

`packages/casebench-tr/` in this repository is the reference adapter for Türkiye.

The `plugin new` and `plugin test` commands arrive with the plugin contract; until then, this file describes the target.
