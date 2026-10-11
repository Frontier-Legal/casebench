# Adding a jurisdiction

Lawyer-authored cases work in any country with no adapter. Court-derived references and citation checks need an adapter for the country: code that knows how its courts write decisions and cite law.

## What an adapter does

- Parses the country's citation formats for decisions and statutes.
- Finds the operative part of a decision, so facts can end before the ruling.
- Maps courts to levels, so a suite can be stratified by court.
- Optionally, looks up the version of a statute article in force on a date.

The adapter reads decisions; it never fetches them. Where decisions come from is a corpus connector's job, and the two are bound per corpus in `casebench.yaml`. One connector can serve several countries.

## Two routes

**Built in.** The adapter lives in this repository under `casebench/jurisdictions/<code>/`, ships inside the `casebench` package and loads only when a config names its code. Choose this when you want the maintainers to review and release it with the core. `casebench/jurisdictions/tr/` is the reference.

**Your own package.** The adapter ships as `casebench-<code>` from your own repository, on your own release schedule, with no pull request here. It registers the same entry point, so users install it next to `casebench` and select it the same way.

Both routes implement the same interface and pass the same conformance suite.

## Steps

1. Scaffold the adapter: `casebench plugin new adapter --name <code>`. It writes the interface stubs, a conformance test and a README, either as a folder for the built-in route or as a `casebench-<code>` package.
2. Add sample decisions and the extractions a person checked by hand to the adapter's `samples/` folder. Use decisions you are allowed to redistribute.
3. Implement the interface until `casebench plugin test <path>` passes. It checks citation parsing, operative-part extraction and statute lookup against your samples and prints your measured extraction accuracy.
4. Built in: open a pull request. Your own package: publish it to PyPI as `casebench-<code>`.
5. Open an issue with the "A new jurisdiction" template so the README can list the adapter with its measured figures.

Heavy dependencies, such as a morphology library, go behind an extra named after the code (`casebench[tr]`), never into the core's required dependencies.

`casebench plugin kinds` lists every plugin kind with its entry-point group and interface. Decision [0016](docs/decisions/0016-plugin-contract.md) explains the contract.
