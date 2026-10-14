# Adding a plugin

Casebench works in any country with no country-specific code ([decision 0024](docs/decisions/0024-no-jurisdiction-adapters.md)). What contributors add are plugins: where decisions come from, how to read a model API's traffic, and how Casebench calls its own judge and extraction models.

| Kind | What it does | Entry-point group | Measured by `plugin test` |
|---|---|---|---|
| connector | lists and fetches decisions and statutes from a store: a folder, S3, a database, a provider's API | `casebench.corpus` | share of required fields present |
| parser | reads one model API's calls through the recording proxy | `casebench.capture` | share of recorded calls parsed |
| provider | builds requests to, and reads responses from, a model API for Casebench's own judge and extraction | `casebench.providers` | share of recorded responses parsed |

`casebench plugin kinds` lists every kind, the others included, with its interface.

A store reachable over HTTP or MCP needs no plugin at all: `casebench corpus add http` or `casebench corpus add mcp` makes one live search and fetch, suggests where each field is, and writes the connector into casebench.yaml. A provider can save those answers as a profile file, so its users run `casebench corpus add profile provider.yaml` or `casebench init --profile provider.yaml` and answer nothing ([decision 0033](docs/decisions/0033-data-provider-profiles.md)); `casebench validate provider.yaml` checks the file. A setup may connect several stores, one per jurisdiction for example: each `corpus add` adds one more under its own name (`--name`, or one made from the store), with the jurisdictions it covers (`--jurisdiction NO`) ([decision 0036](docs/decisions/0036-several-corpora.md)). Write a connector plugin only for a store neither can reach.

A model provider takes the model settings its API documents as constructor arguments, under the names Casebench uses everywhere (`reasoning_effort`, `thinking_budget`, `temperature`, `max_tokens`), and sends each in the form its vendor documents; one not set is not sent. Casebench refuses a setting a provider does not take before any call ([decision 0038](docs/decisions/0038-model-settings-by-measurement.md)).

A parser may list `packages`, the SDKs whose calls it reads (such as `openai` on PyPI or `@anthropic-ai/sdk` on npm), so `casebench init` names them when it finds them in a project's dependency files. It may also list `clients`, the client classes whose calls it reads (such as `openai.OpenAI`), so `casebench init` finds where the code builds them, where their base URL comes from, and offers each a capture route ([decision 0040](docs/decisions/0040-init-reads-the-code.md)).

A connector holds no legal logic. One connector can serve many countries; each decision carries its jurisdiction, and a corpus in `casebench.yaml` may name one to filter by.

The judge matches a citation by what the store says about each search result: how it cites the document, its type and the passage the search matched. A connector whose store returns these also defines `search_results(text, limit, filters)`, returning `casebench.corpus.results.SearchResult` items, and applies `filters`, which `casebench.yaml` sets per kind of citation under `search_filters`. The `http` and `mcp` connectors read them with `search_results` and `result_fields`, which `corpus add` suggests and `corpus check` reports on. A connector with only `search(text, limit)` still works: Casebench fetches each candidate and describes it from the document ([decision 0037](docs/decisions/0037-match-by-the-corpus-description.md)).

## Steps

1. Scaffold it: `casebench plugin new <kind> --name <name>`. It writes a `casebench-<name>` package with the interface stubs, a conformance test and a README. With `--built-in`, it writes a folder inside the core instead, for a plugin the maintainers will release with Casebench.
2. Add samples to the plugin's `samples/` folder: recorded calls for a parser or provider, a small store and its `config.json` for a connector. Use only data you are allowed to redistribute.
3. Implement the interface until `casebench plugin test <path>` passes. It prints the figure it measured.
4. Publish your package to PyPI as `casebench-<name>`, or open a pull request for a built-in one.

## A profile bundled with Casebench

`casebench init` lists bundled profiles by name only, and preselects one only when its key is set on the user's machine. Every provider meets the same bar ([decision 0033](docs/decisions/0033-data-provider-profiles.md)):

1. Write `casebench/corpus/profiles/<id>.yaml`, with a `maintainer` who answers issues about it. Check it with `casebench validate`.
2. Record one search and one fetch, which you may publish, as `casebench/corpus/profiles/samples/<id>/search.json` and `fetch.json`.
3. Run `uv run pytest tests/corpus/test_bundled_profiles.py`. It reads the recordings through the profile's paths, with no network and no key.
4. Open a pull request. A profile you do not bundle works the same way as a file your users pass to `--profile`.
