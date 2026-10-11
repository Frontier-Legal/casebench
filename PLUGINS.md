# Adding a plugin

Casebench works in any country with no country-specific code ([decision 0024](docs/decisions/0024-no-jurisdiction-adapters.md)). What contributors add are plugins: where decisions come from, how to read a model API's traffic, and how Casebench calls its own judge and extraction models.

| Kind | What it does | Entry-point group | Measured by `plugin test` |
|---|---|---|---|
| connector | lists and fetches decisions and statutes from a store: a folder, S3, a database, a provider's API | `casebench.corpus` | share of required fields present |
| parser | reads one model API's calls through the recording proxy | `casebench.capture` | share of recorded calls parsed |
| provider | builds requests to, and reads responses from, a model API for Casebench's own judge and extraction | `casebench.providers` | share of recorded responses parsed |

`casebench plugin kinds` lists every kind, the others included, with its interface.

A store reachable over HTTP or MCP needs no plugin at all: `casebench corpus add http` or `casebench corpus add mcp` makes one live search and fetch, suggests where each field is, and writes the connector into casebench.yaml. Write a connector plugin only for a store neither can reach.

A parser may list `packages`, the SDKs whose calls it reads (such as `openai` on PyPI or `@anthropic-ai/sdk` on npm), so `casebench init` names them when it finds them in a project's dependency files.

A connector holds no legal logic. One connector can serve many countries; each decision carries its jurisdiction, and a corpus in `casebench.yaml` may name one to filter by.

## Steps

1. Scaffold it: `casebench plugin new <kind> --name <name>`. It writes a `casebench-<name>` package with the interface stubs, a conformance test and a README. With `--built-in`, it writes a folder inside the core instead, for a plugin the maintainers will release with Casebench.
2. Add samples to the plugin's `samples/` folder: recorded calls for a parser or provider, a small store and its `config.json` for a connector. Use only data you are allowed to redistribute.
3. Implement the interface until `casebench plugin test <path>` passes. It prints the figure it measured.
4. Publish your package to PyPI as `casebench-<name>`, or open a pull request for a built-in one.
