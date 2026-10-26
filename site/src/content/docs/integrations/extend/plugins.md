---
title: Write a plugin or a profile
description: Add a document store, a model API parser, a judge provider or any other plugin kind as its own package, scaffolded and checked by a conformance test.
sidebar:
  order: 1
---

Everything outside Casebench's core is a plugin, found through Python entry points: where documents come from, how a model API's traffic is read, how Casebench calls its own models, and more. Each kind has an interface and a conformance test in the core.

Before writing code, check whether you need to:

- A document store reachable over HTTP or MCP needs no plugin. `casebench corpus add http` or `mcp`, or the workbench's Jurisdictions page, connects it, and a [profile](/integrations/stores/provider-profiles/) shares that setup with others.
- A model provider whose API is compatible with OpenAI's Chat Completions or Anthropic's Messages needs no plugin: the `openai` or `anthropic` provider reaches it by `base_url`.
- A new jurisdiction needs no plugin. Casebench has no country-specific code.

## Plugin kinds

```sh
casebench plugin kinds
```

| Kind | Does | Entry-point group | `plugin test` measures |
| --- | --- | --- | --- |
| `connector` | Lists, searches and fetches documents from a store | `casebench.corpus` | Fields covered |
| `parser` | Reads one model API's calls through the recording proxy | `casebench.capture` | Calls parsed |
| `provider` | Builds requests to, and reads responses from, a model API for the judge and extraction | `casebench.providers` | Responses parsed |
| `task` | A task type: its input, its output, its default metrics | `casebench.tasks` | |
| `reference` | Builds references for cases | `casebench.references` | |
| `target` | A way to reach the AI under test | `casebench.targets` | |
| `metric` | Scores one aspect of an output | `casebench.metrics` | |
| `exporter` | Writes cases and scores into another tool | `casebench.exporters` | |

When two installed distributions register the same name, `connector_source`, `provider_source` or a target's `source` in `casebench.yaml` says which one to load.

## Steps

1. Scaffold it.

   ```sh
   casebench plugin new connector --name acme
   ```

   It writes a `casebench-acme` package with the interface stubs, a `casebench-plugin.json`, a conformance test, a `samples/` folder and a README, and prints how to install it: `uv pip install -e casebench-acme`. With `--built-in` it writes a folder inside the core instead, for a plugin the maintainers will release with Casebench. `--root` says where to write.

2. Add samples to the plugin's `samples/` folder: recorded calls for a parser or a provider, a small store and its `config.json` for a connector. Use only data you may redistribute.

3. Implement the interface until the conformance test passes. It prints the figure it measured. A fresh scaffold fails, naming the interface it does not meet yet.

   ```sh
   casebench plugin test ./casebench-acme
   ```

4. Publish the package to PyPI as `casebench-<name>`, or open a pull request for a built-in one.

## What each kind should declare

- A connector holds no legal logic. One connector can serve many countries; each document carries its jurisdiction. A connector whose store describes search results defines `search_results(text, limit, filters)` returning `casebench.corpus.results.SearchResult` items, and applies `filters`. One with only `search(text, limit)` still works: Casebench fetches each candidate and describes it from the document.
- A parser may list `packages`, the SDKs whose calls it reads (such as `openai` on PyPI or `@anthropic-ai/sdk` on npm), and `clients`, the client classes (such as `openai.OpenAI`), so `casebench init` finds them in a project. A parser that declares a `default_route` gets that route in every run.
- A provider takes the model settings its API documents as constructor arguments, under Casebench's names (`reasoning_effort`, `thinking_budget`, `temperature`, `max_tokens`, `model_fields`), and sends each in the form its vendor documents. One not set is not sent, and one it does not take is refused before any call. An HTTP provider builds a request and reads a response, and the core sends it, so the network perimeter applies. An SDK provider has `complete(messages, model)` and calls the vendor's SDK installed in the project. A provider may list `speaks`, the model catalog's API packages it speaks, so `casebench init` fills from the catalog the options its constructor takes: `base_url`, `api_key_env`, `family`, and `max_tokens` where it requires one. It may list `packages` too, the SDKs it needs, which `casebench check` looks for.

## Bundle a profile with Casebench

1. Write `casebench/corpus/profiles/<id>.yaml`, with a `maintainer` who answers issues about it, and check it with `casebench validate`.
2. Record one search and one fetch you may publish, as `casebench/corpus/profiles/samples/<id>/search.json` and `fetch.json`.
3. Run the bundled-profile test, which reads the recordings through the profile with no network and no key:

   ```sh
   uv run pytest tests/corpus/test_bundled_profiles.py
   ```

4. Open a pull request. A profile you do not bundle works the same way as a file your users pass to `--profile`.

Casebench 0.5.1 bundles no profile yet. Every profile meets the same bar and is listed the same way: by name, in alphabetical order.
