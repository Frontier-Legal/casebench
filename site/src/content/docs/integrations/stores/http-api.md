---
title: Document API over HTTP
description: Connect any document API that can search and fetch by id, with JSONPath for each field picked from one live search and fetch, at a terminal, from a coding agent or in the workbench.
sidebar:
  order: 1
---

The `http` connector reaches any API that can fetch a document by id and search. Casebench ships no preset for any provider. It reads whatever JSON the API returns through JSONPath expressions you confirm once, each picked from a real search and a real fetch.

## Add it

There are three ways, and each writes the same block to `casebench.yaml`.

### At a terminal

```sh
casebench corpus add http
```

It asks for the base URL, the search and fetch paths and the variable holding the key. Then it makes one search with a query you give, shows the JSON that came back, and asks where each result keeps its id, citation, type and passage. It fetches the first result and asks which field of the document is its id, jurisdiction, court, date, text and level. The id, text and date are suggested from the values alone: the field that holds the id the document was fetched by, the longest text, and the first value in ISO date form. Court and jurisdiction are yours to pick, since nothing in a value says which it is.

Every answer can be a flag, and `--yes` takes the flags and suggestions without asking. See [`corpus add http`](/developers/reference/cli/#casebench-corpus-add-http).

### From a coding agent or a script

```sh
casebench corpus probe http --base-url '${DOCS_URL}' --key-env DOCS_KEY --query "notice period"
casebench corpus probe http --base-url '${DOCS_URL}' --key-env DOCS_KEY --fetch doc-1842
```

`corpus probe http` makes one search, one fetch, or both, and prints each response as JSON. The key is found by name, in the shell or the project's `.env` files, and never shown. Whoever reads the output then maps the fields by flag:

```sh
casebench corpus add http --base-url '${DOCS_URL}' --key-env DOCS_KEY \
  --search-path /search --fetch-path '/documents/{id}' --probe "notice period" \
  --results '$.results[*]' --result-field id='$.id' --result-field passage='$.highlight' \
  --field id='$.id' --field jurisdiction='$.country' --field court='$.court.name' \
  --field date='$.decided_on' --field text='$.body' --jurisdiction GB --yes
```

### In the workbench

On the Jurisdictions page, pick a country by name, then a document API as its source. The workbench makes one search and shows the first result field by field, with its values. You pick the id, and may pick the citation, type and passage; it fetches one document and suggests its id, text and date from their values. Nobody writes a JSONPath. A source that answers but holds no document Casebench can read does not pass its test.

## The block it writes

`corpus add` adds a named entry under `corpora:`, named after the API's host unless `--name` gives another. It never replaces a corpus already there.

```yaml title="casebench.yaml"
corpora:
  api-example-com:
    connector: http
    jurisdictions: [GB]
    options:
      base_url: https://api.example.com/v1
      headers:
        Authorization: Bearer ${EXAMPLE_API_KEY}
      search_path: /search
      search_params: { q: "{text}" }
      fetch_path: /documents/{id}
      search_results: $.results[*]
      result_fields:
        id: $.id
        citation: $.citation
        passage: $.highlight
      fields:
        id: $.id
        jurisdiction: $.jurisdiction
        court: $.court.name
        date: $.decided_on
        text: $.body
    probe: notice period
```

`probe` is the search the corpus was added with. `casebench check` and `corpus check` run it when no `--query` is given.

| Placeholder | Filled with |
| --- | --- |
| `{text}` | The search text |
| `{limit}` | How many results are wanted |
| `{id}` | The document id, in `fetch_path` |
| `${NAME}` | The variable, read from the shell or a `.env` file `keys:` names, in `headers` and `base_url`. One set nowhere is an error naming it. |

Every option is listed in the [configuration reference](/developers/reference/configuration/#http-options).

## Keys and the address

`--key-env NAME` names the variable that holds the key. With the default `--key-header Authorization`, the key is sent as `Bearer ${NAME}`; another header, such as `--key-header x-api-key`, sends it as it is. `corpus add` refuses a key typed in place of the variable in `Authorization` or `Proxy-Authorization`. A key in a `.env` file is found by name, and `--key NAME=FILE` says which file when several hold it.

The base URL may be a variable too, such as `--base-url '${DOCS_URL}'`. A project that keeps the store's address in a `.env` file is connected without anyone opening that file, and `casebench.yaml` names the variable rather than holding the URL.

## Search by POST

For an API that searches with a JSON body, give the body:

```sh
casebench corpus add http --search-body '{"query": "{text}", "limit": "{limit}"}' ...
```

A search is then a POST of that body to `search_path`. `"{limit}"` alone becomes a number. A search filter, such as a document type, is added to the body as a field instead of a query parameter.

## Fields Casebench needs from a document

`id`, `jurisdiction`, `court`, `date` and `text`, plus `level` when the store gives court levels, which `generate --stratify court` needs. `casebench corpus check` reports each field present or missing on a sample, and a field the expressions cannot find is named.

## The agent's own API is fine

If your agent retrieves from the same API, use it as the corpus too. When the agent is a Python target, its searches of that API during a run are recorded as retrievals, with the ids the corpus's search results hold, and its fetches as documents. Casebench refuses only a corpus whose URL is the HTTP target's own endpoint: a system must not confirm its own citations.

## Related

- [Connect a document store](/developers/guides/connect/document-store/).
- [Provider profiles](/integrations/stores/provider-profiles/), to share a working setup.
- [Manage the corpus cache](/developers/guides/maintain/corpus-cache/).
